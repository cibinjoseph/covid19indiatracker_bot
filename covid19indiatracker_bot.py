""" A Telegram bot to retrieve stats from the covid19india.org site """
from sys import version_info
# if version_info.major > 2:
#     raise Exception('This code does not work with Python 3. Use Python 2')
import requests
import json
import operator
from telegram import ParseMode
from telegram.ext import Updater, CommandHandler
import logging

# Bot details
_tokenFile = 'TOKEN'
logging.basicConfig(filename='covid19indiatracker_bot.log',
                    format='%(asctime)s - %(name)s - \
                    %(levelname)s - %(message)s',
                    level=logging.INFO)
webPageLink = 'https://www.covid19india.org'
MOHFWLink = "https://www.mohfw.gov.in/dashboard/data/data.json"
_stateNameCodeDict = {}


def _getSiteData(statewise=False):
    """ Retrieves data from api link """
    if statewise == False:
        link = 'https://api.covid19india.org/data.json'
    else:
        link = 'https://api.covid19india.org/v2/state_district_wise.json'
    try:
        data = requests.get(link).json()
        logging.info('Stats retrieval: SUCCESS')
        return data
    except:
        logging.info('Stats retrieval: FAILED')
        return None


def _getMOHFWData():
    """ Retrieves data from MOHFW site """
    logging.info('Command invoked: covid19india')
    link = MOHFWLink
    try:
        data = requests.get(link).json()
        logging.info('Stats retrieval: SUCCESS')
        return data
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


def _getSortedStatewise(data):
    """ Returns ordered statewise data on the basis of max confirmed"""
    stateConfirmed = {}
    for state in data:
        totalConfirmed = 0
        for district in state['districtData']:
            totalConfirmed = totalConfirmed + int(district['confirmed'])
        stateConfirmed[state['state']] = totalConfirmed
    sortedData = sorted(stateConfirmed.items(), key=operator.itemgetter(1),
                        reverse=True)
    return(sortedData)


def _getSortedNational(data, keyBasis='active'):
    """ Returns ordered national data on the basis of max confirmed"""
    stateValue = {}
    for state in data['statewise']:
        stateName = str(state['state'])
        value = int(state[keyBasis])
        stateValue[stateName] = value
    orderedData = sorted(stateValue.items(), key=operator.itemgetter(1),
                         reverse=True)
    return(orderedData)


def _getMessageNational():
    """ Returns formatted data for printing """
    data = _getSiteData()
    orderedData = _getSortedNational(data)
    chars = 5  # Character spacing per column
    message = '\n' \
    + webPageLink \
    + '\n\n' \
    + 'REGION'.ljust(5, '.') + '|'\
    + 'CONF'.ljust(5, '.') + '|'\
    + 'RECO'.ljust(5, '.') + '|'\
    + 'DECE'.ljust(5, '.') + '|'\
    + 'ACTI'.ljust(5, '.') + '\n'\
    + '------|-----|-----|-----|-----\n'

    for state in orderedData:
        stateName = state[0]
        # Find rest of the values from dataset
        for stateDict in data['statewise']:
            if stateName == stateDict['state']:
                if stateName.strip() != 'Total':
                    stateName = stateName[0:6].ljust(6, ' ')
                else:
                    stateName = 'INDIA.'
                code = stateDict["statecode"].ljust(chars, ' ')
                active = stateDict["active"].ljust(chars, ' ')
                confirmed = stateDict["confirmed"].ljust(chars, ' ')
                deaths = stateDict["deaths"].ljust(chars, ' ')
                recovered = stateDict["recovered"].ljust(chars, ' ')
                # deltaconfirmed = state["deltaconfirmed"]
                # deltadeaths    = state["deltadeaths"]
                # deltarecovered = state["deltarecovered"]
        message = message + stateName + '|' \
            + confirmed + '|' + recovered + '|' \
            + deaths + '|' + active + '\n'
    message = '```' + message + '```'
    return message


def _getMessageStatewise(stateName):
    data = _getSiteData(statewise=True)
    chars = 8
    for stateDict in data:
        if stateName == stateDict['state']:
            message = webPageLink + '\n' +  \
                'District'.ljust(14,' ') + '|Total Confirmed'.ljust(14,' ') + '\n'
            for district in stateDict['districtData']:
                districtName = district['district']
                confirmed = str(district['confirmed']).ljust(chars, ' ')
                delta = str(district['delta']['confirmed']).ljust(chars, ' ')
                message = message + districtName[0:10].ljust(14, '.') \
                    + '|' + confirmed + '\n'
            break
    message = '```' +  message + '```'
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
              "/covid19india <state> - Displays stats of a <state>\n" + \
              "/statecodes - Displays codes of states that can be used as <state>\n" + \
              "/mohfw - Displays the difference in cases reported by MOHFW\n" + \
              "(-ve) means MOHFW reports lesser cases and\n(+ve) means MOHFW reports higher cases than covid19india.org"

    context.bot.send_message(chat_id=update.effective_chat.id, text=message)


def statecodes(update, context):
    """ Displays state codes """
    logging.info('Command invoked: statecodes')
    global _stateNameCodeDict
    message = ''
    for stateName in _stateNameCodeDict:
        if len(stateName) == 2:
            message = message + stateName + ': ' + \
                _stateNameCodeDict[stateName] + '\n'

    message = webPageLink + '\n```'+ 'State codes\n\n' + message + '```'

    context.bot.send_message(chat_id=update.effective_chat.id, text=message,
                             parse_mode=ParseMode.MARKDOWN,
                             disable_web_page_preview=True)


def covid19india(update, context):
    """ Main command that retrieves and sends data """
    logging.info('Command invoked: covid19india')
    # Check for arguments
    stateName = "".join(context.args).strip().upper()
    if len(stateName) > 1:  # State data requested
        try:
            stateName = _stateNameCodeDict[stateName]
            message = _getMessageStatewise(stateName)
        except KeyError:
            message = 'Invalid state name. Use /statecodes to display codes.'
    else:  # National data requested
        message = _getMessageNational()

    context.bot.send_message(chat_id=update.effective_chat.id, text=message,
                             parse_mode=ParseMode.MARKDOWN,
                             disable_web_page_preview=True)


def mohfw(update, context):
    """ Compares covid19india.org data with MOHFW database """
    dataSITE_raw = _getSiteData()
    dataSITE = _getSortedNational(dataSITE_raw, keyBasis='active')[1:]
    dataMOHFW = _getMOHFWData()
    message = 'MOHFW Reports : ' \
        + '\n\n' \
        + 'REGION'.ljust(8, '.') + '|'\
        + 'CNFRD'.ljust(6, '.') + '|'\
        + 'RCVRD'.ljust(6, '.') + '|'\
        + 'DECSD'.ljust(6, '.') + '\n'\
        + '--------|------|------|------\n'
    chars = 6

    for state in dataSITE:
        stateSITE = str(state[0])
        activeSITE = state[1]
        # Obtain deaths and recovered for each state from site dataset
        for stateDict in dataSITE_raw['statewise']:
            if stateSITE == stateDict['state']:
                confirmedSITE = int(stateDict['confirmed'])
                deathsSITE = int(stateDict['deaths'])
                recoveredSITE = int(stateDict['recovered'])

        confirmedMOHFW = 'UNAVBL'
        for stateDict in dataMOHFW:
            stateMOHFW = str(stateDict['state_name'])
            # Check for matching state name in MOHFW database
            # 1. Handle Telangana misspelling
            if stateMOHFW == stateSITE or \
               (stateSITE == 'Telangana' and stateMOHFW == 'Telengana'):
                confirmedMOHFW = stateDict['positive']
                recoveredMOHFW = stateDict['cured']
                deathsMOHFW = stateDict['death']
        if confirmedMOHFW == 'UNAVBL':
            confirmedMOHFW = 'UNAVBL'.ljust(chars, ' ')
            active_diff = 'UNAVBL'.ljust(chars, ' ')
            recovered_diff = 'UNAVBL'.ljust(chars, ' ')
            deaths_diff = 'UNAVBL'.ljust(chars, ' ')
            activeMOHFW = 'UNAVBL'.ljust(chars, ' ')
        else:
            confirmed_diff = int(confirmedMOHFW) - confirmedSITE
            active_diff = int(confirmedMOHFW) - int(recoveredMOHFW) - \
                int(deathsMOHFW) - activeSITE
            recovered_diff = int(recoveredMOHFW) - recoveredSITE
            deaths_diff = int(deathsMOHFW) - deathsSITE
            # String formatting
            confirmed_diff = '{0:+}'.format(confirmed_diff).ljust(chars, ' ')
            active_diff = '{0:+}'.format(active_diff).ljust(chars, ' ')
            recovered_diff = '{0:+}'.format(recovered_diff).ljust(chars, ' ')
            deaths_diff = '{0:+}'.format(deaths_diff).ljust(chars, ' ')
            # Check for +0 and change to _0
            if confirmed_diff.strip() == '+0':
                confirmed_diff = ' 0'.ljust(chars, ' ')
            if active_diff.strip() == '+0':
                active_diff = ' 0'.ljust(chars, ' ')
            if recovered_diff.strip() == '+0':
                recovered_diff = ' 0'.ljust(chars, ' ')
            if deaths_diff.strip() == '+0':
                deaths_diff = ' 0'.ljust(chars, ' ')

        message = message + \
            stateSITE[0:chars+2].ljust(chars+2, '.') + \
            '|' + confirmed_diff + '|' + recovered_diff + \
            '|' + deaths_diff + '\n'

    message = '```' + message + '```'

    context.bot.send_message(chat_id=update.effective_chat.id, text=message,
                             parse_mode=ParseMode.MARKDOWN,
                             disable_web_page_preview=True)


def main():
    logging.info('covid19india_bot started')

    _initStateCodes('statecodes.json')
    updater = Updater(token=_readToken(_tokenFile), use_context=True)

    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('help', help))
    updater.dispatcher.add_handler(
        CommandHandler('covid19india', covid19india))
    updater.dispatcher.add_handler(CommandHandler('statecodes', statecodes))
    updater.dispatcher.add_handler(CommandHandler('mohfw', mohfw))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
    logging.info('Program end')
