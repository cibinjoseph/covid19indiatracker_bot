""" A Telegram bot to retrieve stats from the covid19india.org site """
import json, requests
import logging
from telegram.ext import Updater, CommandHandler
from telegram import ParseMode
import operator

# Bot details
_tokenFile = 'TOKEN'
logging.basicConfig(filename='covid19indiatracker_bot.log', \
                    format='%(asctime)s - %(name)s - \
                    %(levelname)s - %(message)s', \
                    level=logging.INFO)
webPageLink = 'https://www.covid19india.org'
_stateNameCodeDict = {}

def _getData(statewise=False):
    """ Retrieves data from api link """
    if statewise == False:
        link = 'https://api.covid19india.org/data.json'
    else:
        link = 'https://api.covid19india.org/v2/state_district_wise.json'
    try:
        data = requests.get(link).json()
        return data
        logging.info('Stats retrieval: SUCCESS')
    except:
        logging.info('Stats retrieval: FAILED')
        return None

def _readToken(filename):
    """ Read secret Bot TOKEN from file """
    with open(filename, 'r') as f:
        TOKEN = f.readline().strip()
    if not TOKEN:
        raise ValueError('TOKEN not found in file: ' + filename)
    else:
        return TOKEN

def _getOrderedState(data):
    """ Returns ordered statewise data on the basis of max confirmed"""
    stateConfirmed = {}
    for state in data:
        totalConfirmed = 0
        for district in state['districtData']:
            totalConfirmed = totalConfirmed + int(district['confirmed'])
        stateConfirmed[state['state']] = totalConfirmed
    orderedData = sorted(stateConfirmed.items(), key=operator.itemgetter(1), \
                        reverse=True)
    return(orderedData)

def _getOrderedNational(data, keyBasis='active'):
    """ Returns ordered national data on the basis of max confirmed"""
    stateValue = {}
    for state in data['statewise']:
        stateName = str(state['state'])
        value = int(state[keyBasis])
        stateValue[stateName] = value
    orderedData = sorted(stateValue.items(), key=operator.itemgetter(1), \
                        reverse=True)
    return(orderedData)

def _getNationalStats():
    """ Returns formatted data for printing """
    data = _getData()
    orderedData = _getOrderedNational(data)
    chars = 5  # Character spacing per column
    message = webPageLink + '\n' + \
            '*Active*| *Recovered* ' +\
            '*Deceased* | *Total* ``` \n'
    for state in orderedData:
        stateName = state[0]
        # Find rest of the values from dataset
        for stateDict in data['statewise']:
            if stateName == stateDict['state']:
                if stateName.strip() != 'Total':
                    stateName = stateName[0:6].ljust(6, '.')
                else:
                    stateName = 'SUM'.ljust(3,'.')
                code           = stateDict["statecode"].ljust(chars, ' ')
                active         = stateDict["active"].ljust(chars, ' ')
                confirmed      = stateDict["confirmed"].ljust(chars, ' ')
                deaths         = stateDict["deaths"].ljust(chars, ' ')
                recovered      = stateDict["recovered"].ljust(chars, ' ')
                # deltaconfirmed = state["deltaconfirmed"]
                # deltadeaths    = state["deltadeaths"]
                # deltarecovered = state["deltarecovered"]
        message = message + stateName + '|' \
            + active + '|' + recovered + '|' \
            + deaths + '|' + confirmed + '\n'
    message = message + ' ```'
    return message

def _getStatewiseStats(stateName):
    data = _getData(statewise=True)
    chars = 8
    for stateDict in data:
        if stateName == stateDict['state']:
            message = webPageLink + '\n' +  \
                    '*District* | *Total Confirmed* ``` \n'
            for district in stateDict['districtData']:
                districtName = district['district']
                confirmed = str(district['confirmed']).ljust(chars, ' ')
                delta = str(district['delta']['confirmed']).ljust(chars, ' ')
                message = message + districtName[0:10].ljust(14, '.') \
                        + '|' + confirmed + '\n'
            break
    message = message + '```'
    return message

def _initStateCodes(filename):
    global _stateNameCodeDict
    with open(filename, 'r') as scFile:
        _stateNameCodeDict = json.load(scFile)

def start(update, context):
    """ start command """
    logging.info('Command invoked: start')
    message = 'Use /help for a list of commands.'
    context.bot.send_message(chat_id=update.effective_chat.id, text=message)

def help(update, context):
    """ help command """
    logging.info('Command invoked: help')
    message = "/covid19india - Displays stats of all states\n" + \
              "/covid19india <state> - Displays stats of a <state>\n"+ \
              "/statecodes - Displays codes of states that can be used as <state>"
    context.bot.send_message(chat_id=update.effective_chat.id, text=message)

def statecodes(update, context):
    """ Displays state codes """
    logging.info('Command invoked: statecodes')
    global _stateNameCodeDict
    message = ''
    for stateName in _stateNameCodeDict:
        if len(stateName) == 2:
            message = message + stateName + ': ' +  _stateNameCodeDict[stateName] + '\n'
    message = webPageLink + '\n *State codes* ```\n' + message + '```'
    context.bot.send_message(chat_id=update.effective_chat.id, text=message, \
                            parse_mode=ParseMode.MARKDOWN, \
                            disable_web_page_preview=True)

def covid19india(update, context):
    """ Main command that retrieves and sends data """
    logging.info('Command invoked: covid19india')
    # Check for arguments
    stateName = "".join(context.args).strip().upper()
    if len(stateName) > 1:  # State data requested
        try:
            stateName = _stateNameCodeDict[stateName]
            message = _getStatewiseStats(stateName)
        except KeyError:
            message = 'Invalid state name. Use /statecodes to display codes.'
    else:  # National data requested
        message = _getNationalStats()
    context.bot.send_message(chat_id=update.effective_chat.id, text=message, \
                            parse_mode=ParseMode.MARKDOWN, \
                            disable_web_page_preview=True)

def main():
    logging.info('covid19india_bot started')

    _initStateCodes('statecodes.json')
    updater = Updater(token=_readToken(_tokenFile), use_context=True)

    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('help', help))
    updater.dispatcher.add_handler(CommandHandler('covid19india', covid19india))
    updater.dispatcher.add_handler(CommandHandler('statecodes', statecodes))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
    logging.info('Program end')
