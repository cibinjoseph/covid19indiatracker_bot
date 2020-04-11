import json

with open('statecodes.txt', 'r') as stc:
    lines = stc.readlines()

stateCodeDict = {}
for line in lines:
    stateCode = line[-3:-1]
    stateName = line[:-3].strip()
    # Match code to state name
    stateCodeDict[stateCode] = stateName
    # Match state name to state name
    stateCodeDict[stateName.upper()] = stateName

with open('statecodes.json', 'w') as outfile:
    json.dump(stateCodeDict, outfile)

