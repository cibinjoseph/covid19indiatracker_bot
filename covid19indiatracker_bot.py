""" A Telegram bot to retrieve stats from the covid19india.org site """
from sys import version_info
# if version_info.major > 2:
#     raise Exception('This code does not work with Python 3. Use Python 2')
import requests
import json
import operator
from telegram import ParseMode
from telegram.ext import Updater, CommandHandler
from telegram.ext.messagehandler import MessageHandler
from telegram.ext.filters import Filters
import logging
import urllib3
from bs4 import BeautifulSoup

# Bot details
_tokenFile = 'TOKEN'
logging.basicConfig(filename='covid19indiatracker_bot.log',
                    format='%(asctime)s - %(name)s - \
                    %(levelname)s - %(message)s',
                    level=logging.INFO)
_allowRequests = True
_allowRequestsReply = False

webPageLink = 'https://www.covid19india.org'
districts_daiyLink = "https://api.covid19india.org/districts_daily.json"
MOHFWAPILink = "https://www.mohfw.gov.in/data/datanew.json"
MOHFWLink = 'https://www.mohfw.gov.in'
NDMALink = 'https://utility.arcgis.com/usrsvcs/servers/83b36886c90942ab9f67e7a212e515c8/rest/services/Corona/DailyCasesMoHUA/MapServer/0/query?f=json&where=1%3D1&returnGeometry=true&spatialRel=esriSpatialRelIntersects&maxAllowableOffset=9783&geometry=%7B%22xmin%22%3A5009377.085690986%2C%22ymin%22%3A0.000004991888999938965%2C%22xmax%22%3A10018754.171386965%2C%22ymax%22%3A5009377.08570097%2C%22spatialReference%22%3A%7B%22wkid%22%3A102100%7D%7D&geometryType=esriGeometryEnvelope&inSR=102100&outFields=*&outSR=102100&cacheHint=false'
_stateNameCodeDict = {}
unavblCode = 'UNAVBL'.ljust(6, ' ')
zeroCode = ' 0'.ljust(6, ' ')
mohfwDefaultSource = 'api'  # Use 'api' or 'site'


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


def _getMOHFWData(site=False):
    """ Retrieves data from MOHFW API or site"""
    logging.info('Command invoked: _getMOHFWData')
    if site == False:
        # Retrieve data from API
        try:
            data = requests.get(MOHFWAPILink).json()
            logging.info('Stats retrieval: SUCCESS')
            return data
        except:
            logging.info('Stats retrieval: FAILED')
            return None
    else:
        # Retrieve data from web site
        try:
            req = urllib3.PoolManager()
            MOHFWPage = req.request('GET', MOHFWLink)
            soup = BeautifulSoup(MOHFWPage.data, 'html.parser')
            divTag = soup.find('table', attrs={'class': 'table table-striped'})
            rows = divTag.findAll('tr')
            # Discard first row containing header
            rows = rows[1:]

            stateName = []
            active = []
            recovered = []
            deaths = []
            confirmed = []
            for row in rows:
                cols = row.findAll('td')
                if len(cols) == 6:
                    stateName.append(cols[1].text)
                    active.append(cols[2].text)
                    recovered.append(cols[3].text)
                    deaths.append(cols[4].text)
                    confirmed.append(cols[5].text)


            logging.info('Stats retrieval: SUCCESS')
            return stateName, active, recovered, deaths, confirmed
        except:
            logging.info('Stats retrieval: FAILED')
            return None

def _getNDMAData(site=False):
    """ Retrieves data from NDMA API or site """
    logging.info('Command invoked: getNDMAData')
    if site:
        return None
    else:
        # Retrieve data from API
        try:
            data = requests.get(NDMALink).json()
            logging.info('Stats retrieval: SUCCESS')
            return data['features']
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

def _removeSpecialChars(string):
    badChars = ['#', '*', '+']
    for badChar in badChars:
        string = string.replace(badChar,'')
    return string

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
              "/mohfw - Displays data from MOHFW database\n" + \
              "/comparemohfw - Displays the diff. in cases reported by MOHFW database\n" + \
              "(-ve) means MOHFW reports lesser cases and\n(+ve) means MOHFW " + \
              " reports higher cases than covid19india.org\n" + \
              "/request - Forward request to @covid19indiaorg_resource_req\n" + \
              "/advanced - Lists commands and options for advanced usage"

    context.bot.send_message(chat_id=update.effective_chat.id, text=message)

def advanced(update, context):
    """ advanced command """
    logging.info('Command invoked: advanced')

    message = "/request <enable/disable> - admin allow/dissallow requests\n" + \
              "/recon - for value checks in data fields.\n" + \
              " Use the keyword 'api' or 'site' after the commands" + \
              " /mohfw and /comparemohfw for retrieving data directly" + \
              " from the MOHFW website rather than the API provided by MOHFW\n"

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

    message = webPageLink + '```'+ '\n\nState codes\n\n' + message + '```'

    context.bot.send_message(chat_id=update.effective_chat.id, text=message,
                             parse_mode=ParseMode.MARKDOWN,
                             disable_web_page_preview=True)


def getStateCode(stateName):
    global _stateNameCodeDict
    stateName = _stateNameCodeDict[stateName.upper()]
    for key, value in _stateNameCodeDict.items():
        if stateName == value and len(key) == 2:
            return key
    return None


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

def mohfwapi(update, context, compare=False):
    """ Compares covid19india.org data with MOHFW database """
    logging.info('Command invoked: mohfwapi')
    # Check for arguments
    dataSITE_raw = _getSiteData()
    dataSITE = _getSortedNational(dataSITE_raw, keyBasis='active')[1:]
    dataMOHFW = _getMOHFWData()
    message = '\nMOHFW Reports (API): ' \
        + '\n\n' \
        + 'ST' + '|'\
        + 'ACTIV'.ljust(6, '.') + '|'\
        + 'RCVRD'.ljust(6, '.') + '|'\
        + 'DECSD'.ljust(6, '.') + '|'\
        + 'CNFRD'.ljust(6, '.') + '\n'\
        + '--|------|------|------|------\n'
    chars = 6

    try:
        for state in dataSITE:
            stateSITE = str(state[0])
            activeSITE = state[1]
            # Handle "State Unassigned"
            if (stateSITE == 'State Unassigned'):
                continue
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
                    activeMOHFW = stateDict['new_active']
                    recoveredMOHFW = stateDict['new_cured']
                    deathsMOHFW = stateDict['new_death']
                    confirmedMOHFW = stateDict['new_positive']
                    break

            stateCode = getStateCode(stateSITE)
            if confirmedMOHFW == 'UNAVBL':
                confirmedMOHFW = unavblCode
                confirmed_diff = unavblCode
                active_diff = unavblCode
                recovered_diff = unavblCode
                deaths_diff = unavblCode
                activeMOHFW = unavblCode
            else:
                if compare == True:
                    leadingPlus = '{0:+}'
                    confirmed_diff = int(confirmedMOHFW) - confirmedSITE
                    active_diff = int(activeMOHFW) - activeSITE
                    recovered_diff = int(recoveredMOHFW) - recoveredSITE
                    deaths_diff = int(deathsMOHFW) - deathsSITE
                else:
                    leadingPlus = '{0}'
                    confirmed_diff = int(confirmedMOHFW)
                    active_diff = int(activeMOHFW)
                    recovered_diff = int(recoveredMOHFW)
                    deaths_diff = int(deathsMOHFW)
                # String formatting
                confirmed_diff = leadingPlus.format(confirmed_diff).ljust(chars, ' ')
                active_diff = leadingPlus.format(active_diff).ljust(chars, ' ')
                recovered_diff = leadingPlus.format(recovered_diff).ljust(chars, ' ')
                deaths_diff = leadingPlus.format(deaths_diff).ljust(chars, ' ')
                # Check for +0 and change to _0
                if confirmed_diff.strip() == '+0':
                    confirmed_diff = zeroCode
                if active_diff.strip() == '+0':
                    active_diff = zeroCode
                if recovered_diff.strip() == '+0':
                    recovered_diff = zeroCode
                if deaths_diff.strip() == '+0':
                    deaths_diff = zeroCode

            message = message + \
                stateCode.ljust(2, '.') + \
                '|' + active_diff + '|' + recovered_diff + \
                '|' + deaths_diff + '|' + confirmed_diff + '\n'

        message = '```' + message + '```'

    except TypeError:
        message = 'Data is unavailable. Please try later.'

    context.bot.send_message(chat_id=update.effective_chat.id, text=message,
                             parse_mode=ParseMode.MARKDOWN,
                             disable_web_page_preview=True)

def ndmasite(update, context, compare=False):
    """ Compares covid19india.org data with NDMA website data """
    logging.info('Command invoked: ndmasite')

    message = 'FUNCTION NOT IMPLEMENTED'
    context.bot.send_message(chat_id=update.effective_chat.id, text=message,
                             parse_mode=ParseMode.MARKDOWN,
                             disable_web_page_preview=True)

def ndmaapi(update, context, compare=False):
    """ Compares covid19india.org data with NDMA database """
    logging.info('Command invoked: ndmaapi')
    # Check for arguments
    dataSITE_raw = _getSiteData()
    dataSITE = _getSortedNational(dataSITE_raw, keyBasis='active')[1:]
    dataNDMA = _getNDMAData()
    message = '\nNDMA Reports (API): ' \
        + '\n\n' \
        + 'REGION'.ljust(8, '.') + '|'\
        + 'CNFRD'.ljust(6, '.') + '|'\
        + 'RCVRD'.ljust(6, '.') + '|'\
        + 'DECSD'.ljust(6, '.') + '\n'\
        + '--------|------|------|------\n'
    chars = 6

    try:
        for state in dataSITE:
            stateSITE = str(state[0])
            activeSITE = state[1]
            # Handle "State Unassigned"
            if (stateSITE == 'State Unassigned'):
                continue
            # Obtain deaths and recovered for each state from site dataset
            for stateDict in dataSITE_raw['statewise']:
                if stateSITE == stateDict['state']:
                    confirmedSITE = int(stateDict['confirmed'])
                    deathsSITE = int(stateDict['deaths'])
                    recoveredSITE = int(stateDict['recovered'])

            confirmedNDMA = 'UNAVBL'
            for stateDict in dataNDMA:
                stateNDMA = str(stateDict['attributes']['state_name'])
                # Check for matching state name in MOHFW database
                # 1. Handle Telangana misspelling
                # 2. Handle Dadra '&' Nagar Haveli
                # 3. Daman '&' Diu
                if stateNDMA == stateSITE or \
                   (stateSITE == 'Telangana' and stateNDMA == 'Telengana') or \
                   (stateSITE == 'Dadra and Nagar Haveli' and stateNDMA ==
                    'Dadra & Nagar Haveli') or \
                   (stateSITE == 'Daman and Diu' and stateNDMA == 'Daman & Diu'):
                    confirmedNDMA = stateDict['attributes']['confirmedcases']
                    recoveredNDMA = stateDict['attributes']['cured_discharged_migrated']
                    deathsNDMA = stateDict['attributes']['deaths']
            if confirmedNDMA == 'UNAVBL' or (confirmedNDMA == None) or \
               (recoveredNDMA == None) or (deathsNDMA == None):
                confirmed_diff = 'UNAVBL'.ljust(chars, ' ')
                active_diff = 'UNAVBL'.ljust(chars, ' ')
                recovered_diff = 'UNAVBL'.ljust(chars, ' ')
                deaths_diff = 'UNAVBL'.ljust(chars, ' ')
                activeNDMA = 'UNAVBL'.ljust(chars, ' ')
            else:
                if compare == True:
                    leadingPlus = '{0:+}'
                    confirmed_diff = int(confirmedNDMA) - confirmedSITE
                    active_diff = int(confirmedNDMA) - int(recoveredNDMA) - \
                        int(deathsNDMA) - activeSITE
                    recovered_diff = int(recoveredNDMA) - recoveredSITE
                    deaths_diff = int(deathsNDMA) - deathsSITE
                else:
                    leadingPlus = '{0}'
                    confirmed_diff = int(confirmedNDMA)
                    active_diff = int(confirmedNDMA) - int(recoveredNDMA) - \
                        int(deathsNDMA)
                    recovered_diff = int(recoveredNDMA)
                    deaths_diff = int(deathsNDMA)
                # String formatting
                confirmed_diff = leadingPlus.format(confirmed_diff).ljust(chars, ' ')
                active_diff = leadingPlus.format(active_diff).ljust(chars, ' ')
                recovered_diff = leadingPlus.format(recovered_diff).ljust(chars, ' ')
                deaths_diff = leadingPlus.format(deaths_diff).ljust(chars, ' ')
                # Check for +0 and change to _0
                if confirmed_diff.strip() == '+0':
                    confirmed_diff = zeroCode
                if active_diff.strip() == '+0':
                    active_diff = zeroCode
                if recovered_diff.strip() == '+0':
                    recovered_diff = zeroCode
                if deaths_diff.strip() == '+0':
                    deaths_diff = zeroCode

            message = message + \
                stateSITE[0:chars+2].ljust(chars+2, '.') + \
                '|' + confirmed_diff + '|' + recovered_diff + \
                '|' + deaths_diff + '\n'

        message = '```' + message + '```'

    except TypeError:
        message = 'Data is unavailable. Please try later.'

    context.bot.send_message(chat_id=update.effective_chat.id, text=message,
                             parse_mode=ParseMode.MARKDOWN,
                             disable_web_page_preview=True)

def mohfwsite(update, context, compare=False):
    """ Compares covid19india.org data with MOHFW website data """
    logging.info('Command invoked: mohfwsite')
    dataSITE_raw = _getSiteData()
    dataSITE = _getSortedNational(dataSITE_raw, keyBasis='active')
    try:
        stateScraped, activeScraped, recoveredScraped, \
                deathsScraped, confirmedScraped = _getMOHFWData(site=True)
        message = '\nMOHFW Reports (Site): ' \
            + '\n\n' \
            + 'ST' + '|'\
            + 'ACTIV'.ljust(6, '.') + '|'\
            + 'RCVRD'.ljust(6, '.') + '|'\
            + 'DECSD'.ljust(6, '.') + '|'\
            + 'CNFRD'.ljust(6, '.') + '\n'\
            + '--|------|------|------|------\n'
        chars = 6

        for state in dataSITE:
            stateSITE = str(state[0])
            activeSITE = state[1]
            # Obtain deaths and recovered for each state from site dataset
            for stateDict in dataSITE_raw['statewise']:
                if stateSITE == stateDict['state']:
                    activeSITE = int(stateDict['active'])
                    deathsSITE = int(stateDict['deaths'])
                    recoveredSITE = int(stateDict['recovered'])
                    confirmedSITE = int(stateDict['confirmed'])

            confirmedMOHFW = 'UNAVBL'
            for i in range(len(stateScraped)):
                stateMOHFW = _removeSpecialChars(stateScraped[i])
                # Check for matching state name in MOHFW database
                # 1. Handle Telangana misspelling
                # 2. Handle '#' marks in some state names and cases
                # 3. Handle "State Unassigned"
                # 4. Handle "Dadar Nagar haveli"
                if stateMOHFW == stateSITE or \
                   (stateSITE == 'Telangana' and stateMOHFW == 'Telengana') or \
                   (stateSITE == 'Dadra and Nagar Haveli and Daman and Diu' and \
                    stateMOHFW == 'Dadar Nagar Haveli'):
                    activeMOHFW = _removeSpecialChars(activeScraped[i])
                    recoveredMOHFW = _removeSpecialChars(recoveredScraped[i])
                    deathsMOHFW = _removeSpecialChars(deathsScraped[i])
                    confirmedMOHFW = _removeSpecialChars(confirmedScraped[i])
                    break
                if stateSITE == 'State Unassigned' and \
                   stateMOHFW == 'Cases being reassigned to states':
                    confirmedMOHFW = _removeSpecialChars(confirmedScraped[i])
                    activeMOHFW = _removeSpecialChars(activeScraped[i])
                    deaths_diff = unavblCode
                    recovered_diff = unavblCode
                    break


            stateCode = getStateCode(stateSITE)
            if confirmedMOHFW == 'UNAVBL':
                confirmedMOHFW = unavblCode
                confirmed_diff = unavblCode
                active_diff = unavblCode
                recovered_diff = unavblCode
                deaths_diff = unavblCode
                activeMOHFW = unavblCode
            else:
                if compare == True:
                    leadingPlus = '{0:+}'
                    confirmed_diff = int(confirmedMOHFW) - confirmedSITE
                    active_diff = int(activeMOHFW) - activeSITE
                    if stateSITE != 'State Unassigned':
                        # active_diff = int(confirmedMOHFW) - int(recoveredMOHFW) - \
                        #     int(deathsMOHFW) - activeSITE
                        recovered_diff = int(recoveredMOHFW) - recoveredSITE
                        deaths_diff = int(deathsMOHFW) - deathsSITE
                else:
                    leadingPlus = '{0}'
                    confirmed_diff = int(confirmedMOHFW)
                    active_diff = int(activeMOHFW)
                    if stateSITE != 'State Unassigned':
                        # active_diff = int(confirmedMOHFW) - int(recoveredMOHFW) - \
                        #     int(deathsMOHFW)
                        recovered_diff = int(recoveredMOHFW)
                        deaths_diff = int(deathsMOHFW)
                # String formatting
                confirmed_diff = leadingPlus.format(confirmed_diff).ljust(chars, ' ')
                active_diff = leadingPlus.format(active_diff).ljust(chars, ' ')
                if stateSITE != 'State Unassigned':
                    recovered_diff = leadingPlus.format(recovered_diff).ljust(chars, ' ')
                    deaths_diff = leadingPlus.format(deaths_diff).ljust(chars, ' ')
                # Check for +0 and change to _0
                if confirmed_diff.strip() == '+0':
                    confirmed_diff = zeroCode
                if active_diff.strip() == '+0':
                    active_diff = zeroCode
                if recovered_diff.strip() == '+0':
                    recovered_diff = zeroCode
                if deaths_diff.strip() == '+0':
                    deaths_diff = zeroCode

            message = message + \
                stateCode.ljust(2, '.') + \
                '|' + active_diff + '|' + recovered_diff + \
                '|' + deaths_diff + '|' + confirmed_diff + '\n'

        message = '```' + message + '```'

    except TypeError:
        message = 'Data is unavailable. Please try later.'

    context.bot.send_message(chat_id=update.effective_chat.id, text=message,
                             parse_mode=ParseMode.MARKDOWN,
                             disable_web_page_preview=True)

def mohfw(update, context):
    """ Displays data from MOHFW """
    """ Data retrieved using mohfwDefaultSource variable unless keyword is specified """
    logging.info('Command invoked: mohfw')
    if update.message.text.upper()  == '/MOHFW API':
        logging.info('api keyword provided')
        mohfwapi(update, context, compare=False)
    elif update.message.text.upper() == '/MOHFW SITE':
        logging.info('site keyword provided')
        mohfwsite(update, context, compare=False)
    else:
        if mohfwDefaultSource == 'api':
            logging.info('api source used by default')
            mohfwapi(update, context, compare=False)
        else:
            logging.info('site source used by default')
            mohfwsite(update, context, compare=False)

def comparemohfw(update, context):
    """ Displays difference in data between MOHFW and covid19india.org """
    """ Data retrieved using mohfwDefaultSource variable unless keyword is specified """
    logging.info('Command invoked: comparemohfw')
    if update.message.text.upper()  == '/COMPAREMOHFW API':
        logging.info('api keyword provided')
        mohfwapi(update, context, compare=True)
    elif update.message.text.upper() == '/COMPAREMOHFW SITE':
        logging.info('site keyword provided')
        mohfwsite(update, context, compare=True)
    else:
        if mohfwDefaultSource == 'api':
            logging.info('api source used by default')
            mohfwapi(update, context, compare=True)
        else:
            logging.info('site source used by default')
            mohfwsite(update, context, compare=True)

def ndma(update, context):
    """ Displays data from NDMA """
    """ Data retrieved from API by default unless 'site' is specified """
    logging.info('Command invoked: ndma')
    if update.message.text.upper()  == '/NDMA SITE':
        logging.info('site keyword provided')
        ndmasite(update, context, compare=False)
    else:
        ndmaapi(update, context, compare=False)

def comparendma(update, context):
    """ Displays difference in data between NDMA and covid19india.org """
    """ Data retrieved from SITE by default unless 'api' is specified """
    logging.info('Command invoked: comparendma')
    if update.message.text.upper()  == '/COMPARENDMA SITE':
        logging.info('site keyword provided')
        ndmasite(update, context, compare=True)
    else:
        ndmaapi(update, context, compare=True)

def recon(update, context):
    """ Checks for some invalid values in data """
    logging.info('Command invoked: recon')
    chars = 7
    data = _getSiteData(statewise=True)
    messageHeader = ' Districts with invalid values\n' + \
            '______________________________\n\n' + \
            'ST|DSTRICT|CNFRD..|ACTIV..|\n' + \
            '__________|RCVRD..|DECSD..|\n' + \
            '--|-------|-------|-------|\n'
    message = ''
    messageUn = ''

    for stateDict in data:
        stateCode = stateDict['statecode']
        for districtDict in stateDict['districtData']:
            districtName = districtDict['district']
            active = districtDict['active']
            confirmed = districtDict['confirmed']
            recovered = districtDict['recovered']
            deceased = districtDict['deceased']

            if districtName == 'Unknown':
                if (confirmed != 0) or (recovered != 0) or (deceased != 0):
                    messageUn += stateCode + '|' + \
                            districtName[0:chars].ljust(chars, '.') + '|' + \
                            str(confirmed).ljust(chars, ' ') + '|' + \
                            str(active).ljust(chars, ' ') + '|\n__________|' + \
                            str(recovered).ljust(chars, ' ') + '|' + \
                            str(deceased).ljust(chars, ' ') + '|\n'
            else:
                if (confirmed < 0) or (active < 0) or \
                   (recovered < 0) or (deceased < 0):
                    message += stateCode + '|' + \
                            districtName[0:chars].ljust(chars, '.') + '|' + \
                            str(confirmed).ljust(chars, ' ') + '|' + \
                            str(active).ljust(chars, ' ') + '|\n__________|' + \
                            str(recovered).ljust(chars, ' ') + '|' + \
                            str(deceased).ljust(chars, ' ') + '|\n'

    messageUn += '--|-------|-------|-------|\n'
    message = '```' + messageHeader + messageUn + message + '```'
    context.bot.send_message(chat_id=update.effective_chat.id, text=message,
                             parse_mode=ParseMode.MARKDOWN,
                             disable_web_page_preview=True)

def isAdmin(update, context):
    """ Check if user is admin """
    status = context.bot.get_chat_member( \
                                         chat_id=update.effective_chat.id, \
                                         user_id=update.message.from_user.id)['status']
    chatType = context.bot.get_chat( \
                                    chat_id=update.effective_chat.id \
                                    )['type']

    logging.info('Command invoked by ' + status + ' from ' + chatType + ' chat')
    if status.encode('ascii', 'ignore') == 'member':
        if chatType.encode('ascii', 'ignore') == 'private':
            return True
        return False
    else:
        return True

def request(update, context):
    logging.info('Command invoked: request')
    message = 'Your request has been forwarded'
    global _allowRequests
    global _allowRequestsReply

    # Only allow requests from Covid Ops channel
    if update.message.chat.id ==  -1001263158724:
        if isAdmin(update, context):
            if update.message.text.upper() == '/REQUEST ENABLE REPLY':
                _allowRequestsReply = True
            if update.message.text.upper() == '/REQUEST DISABLE REPLY':
                _allowRequestsReply = False
            if update.message.text.upper() == '/REQUEST ENABLE':
                _allowRequests = True
                message = "Requests are now enabled"
            if update.message.text.upper() == '/REQUEST DISABLE':
                message = "Requests are now disabled"

        if _allowRequests:
            # Forward to requests channel
            context.bot.forward_message(chat_id='@covid19indiaorg_resource_req', \
                                        from_chat_id=update.effective_chat.id, \
                                        message_id=update.message.message_id, \
                                        parse_mode=ParseMode.MARKDOWN, \
                                        disable_web_page_preview=True)

            # Reply to sender with acknowledgement
            if _allowRequestsReply:
                context.bot.send_message(chat_id=update.effective_chat.id, \
                                         text=message, \
                                         parse_mode=ParseMode.MARKDOWN, \
                                         disable_web_page_preview=True, \
                                         disable_notification=True, \
                                         reply_to_message_id=update.message.message_id
                                        )

        if isAdmin(update, context):
            if update.message.text.upper() == '/REQUEST DISABLE':
                _allowRequests = False


def main():
    logging.info('covid19india_bot started')

    _initStateCodes('statecodes.json')
    updater = Updater(token=_readToken(_tokenFile), use_context=True)

    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('help', help))
    updater.dispatcher.add_handler(CommandHandler('covid19india', covid19india))
    updater.dispatcher.add_handler(CommandHandler('statecodes', statecodes))

    updater.dispatcher.add_handler(CommandHandler('mohfw', mohfw))
    updater.dispatcher.add_handler(CommandHandler('comparemohfw', comparemohfw))

    updater.dispatcher.add_handler(CommandHandler('ndma', ndma))
    updater.dispatcher.add_handler(CommandHandler('comparendma', comparendma))

    updater.dispatcher.add_handler(CommandHandler('recon', recon))

    updater.dispatcher.add_handler(CommandHandler('advanced', advanced))

    updater.dispatcher.add_handler(CommandHandler('request', request))
    updater.dispatcher.add_handler(MessageHandler(Filters.regex('#request'), \
                                                  request))


    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
    logging.info('Program end')
