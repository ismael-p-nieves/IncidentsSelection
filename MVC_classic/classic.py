import pandas as pd
import sys
from datetime import datetime

def createList(path):
    incidencias = {}
    controles = {}

    dataframe = pd.read_csv(path, names=['IdIncidencia', 'IdAmenaza', 'Amenaza', 'Gravedad', 'IdControl', 'Control', 'Tiempo'])
    idInc = dataframe['IdIncidencia']
    idCon = dataframe['IdControl']
    grav = dataframe['Gravedad']
    tiem = dataframe['Tiempo']
    incidencias[idInc[0]] = {'gravedad': grav[0], 'tiempo': tiem[0]}
    controles = addControl(controles, idCon[0], idInc[0])

    for i in range(1, len(dataframe.values)):
        if(idInc[i] != idInc[i-1]):
            incidencias[idInc[i]] = {'gravedad': grav[i], 'tiempo': tiem[i]}

        controles = addControl(controles, idCon[i], idInc[i])

    return incidencias, controles, dataframe

def addControl(controles, idControl, idIncidencia):

    for i in controles.keys():
        if i == idControl:
            controles[i].append(idIncidencia)
            return controles

    controles[idControl] = [idIncidencia]
    return controles

def solve(incidencias, controles):
    #solved, rest = find_necessary_incidents(incidencias, controles)

    #remaining = find_already_completed(solved, controles)

    #optimal = find_optimal(rest, remaining, incidencias)

    time1 = datetime.now()
    optimal = find_optimal(incidencias, controles, incidencias)
    time2 = datetime.now()
    totalTime = time2 - time1

    solved = {}
    for i in optimal[0]:
        solved[i] = incidencias[i]

    return solved, totalTime

def find_necessary_incidents(incidencias, controles):
    necessary = {}
    rest = {}

    for i in controles.keys():
        if len(controles[i]) == 1:
            necessary[controles[i][0]] = incidencias[controles[i][0]]
        else:
            for j in controles[i]:
                rest[j] = incidencias[j]

    return necessary, rest

def find_already_completed(incidencias, remaining):
    new_remaining = {}

    for i in remaining.keys():
        done = False
        cIncidencias = remaining[i]
        for j in cIncidencias:
            for k in incidencias.keys():
                if (k == j):
                    done = True

        if (done == False):
            new_remaining[i] = remaining[i]

    return new_remaining

def find_optimal(rest, remaining, incidencias):
    longitud = len(rest)
    optimal = ([], 100000)
    restId = list(rest.keys())

    optimal = recursive_comparation(remaining, incidencias, rest, restId, optimal, longitud, [])

    return optimal

def calculate_time(test, incidencias):
    time = 0
    for i in test:
        time = time + incidencias[i]['tiempo']

    return time
            
def recursive_comparation(remaining, incidencias, rest, restId, optimal, level, state):
    if(level == 1):
        option0 = state.copy()
        if(is_valid(option0, remaining) == True):
            time = calculate_time(option0, incidencias)
            if(time < optimal[1]):
                optimal = (option0, time)

        option1 = state.copy()
        option1.append(restId[len(restId) - level])
        if(is_valid(option1, remaining) == True):
            time = calculate_time(option1, incidencias)
            if(time < optimal[1]):
                optimal = (option1, time)
        
    else:
        option0 = state.copy()
        optimal = recursive_comparation(remaining, incidencias, rest, restId, optimal, level - 1, option0)
        option1 = state.copy()
        option1.append(restId[len(restId) - level])
        optimal = recursive_comparation(remaining, incidencias, rest, restId, optimal, level - 1, option1)

    return optimal

def is_valid(test, controles):
    for i in controles.keys():
        done = False
        cIncidencias = controles[i]

        for j in cIncidencias:
            for k in test:
                if(j == k):
                    done = True

        if(done == False):
            return False

    return True

if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else "sample.csv"
    incidencias, controles, df = createList(path)

    solution, totalTime = solve(incidencias, controles)

    print(solution)
    print(totalTime)