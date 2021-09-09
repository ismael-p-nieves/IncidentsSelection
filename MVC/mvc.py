from dimod.reference.samplers.exact_solver import ExactSolver
from dwave.system.composites.embedding import EmbeddingComposite
import pandas as pd
import dimod
import neal
from dimod import BinaryQuadraticModel
from dwave.system import LeapHybridSampler
from dwave.system import DWaveSampler
import sys
from datetime import datetime
import dwave.inspector

def addControl(controles, idControl, idIncidencia):

    for i in controles.keys():
        if i == idControl:
            controles[i].append(idIncidencia)
            return controles

    controles[idControl] = [idIncidencia]
    return controles

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

    print(incidencias)

    return incidencias, controles, dataframe

def createBQM(incidencias, controles):

    idIncidencias = incidencias.keys()
    idControles = controles.keys()
    Q = dimod.AdjVectorBQM(dimod.Vartype.BINARY)
    J = {}

    tiempos = []
    for i in idIncidencias:
        tiempos.append(incidencias[i]['tiempo'])

    penalizacion = max(tiempos) + 1
    print(tiempos)

    for i, j in zip(idIncidencias, range(len(idIncidencias))):
        Q.set_linear(str(i), tiempos[j])
        J[(i, i)] = tiempos[j]

    for k in idControles:
        cIncidencias = controles[k]
        for i in cIncidencias:
            key = (str(i))

            Q.linear[key] -= penalizacion
            J[(i, i)] -= int(penalizacion)

        for i in range(len(idIncidencias)):
            for j in range(i + 1, len(idIncidencias)):
                incidencia1 = list(idIncidencias)[i]
                incidencia2 = list(idIncidencias)[j]
                
                key = (str(incidencia1), str(incidencia2))
                    
                Q.quadratic[key] = 0
                J[(incidencia1, incidencia2)] = 0

    for k in idControles:
        cIncidencias = controles[k]
        for i in range(len(cIncidencias)):
            for j in range(i + 1, len(cIncidencias)):
                incidencia1 = cIncidencias[i]
                incidencia2 = cIncidencias[j]
                
                key = (str(incidencia1), str(incidencia2))
                
                Q.quadratic[key] += 2 * penalizacion
                J[(incidencia1, incidencia2)] += 2 * penalizacion

    return Q, J

def solve_knapsack(incidencias, controles, sampler=None, samplerSpin=None):
    """Construct BQM and solve the knapsack problem
    
    Args:
        costs (array-like):
            Array of costs associated with the items
        weights (array-like):
            Array of weights associated with the items
        weight_capacity (int):
            Maximum allowable weight
        sampler (BQM sampler instance or None):
            A BQM sampler instance or None, in which case
            LeapHybridSampler is used by default
    
    Returns:
        Tuple:
            List of indices of selected items
            Solution energy
    """

    #solved, rest = find_necessary_incidents(incidencias, controles)

    #remaining = find_already_completed(solved, controles)

    #bqm, J = createBQM(rest, remaining)

    time5 = datetime.now()
    bqm, J = createBQM(incidencias, controles)
    time6 = datetime.now()
    print(time6 - time5)

    print(J)

    time3 = datetime.now()
    sampler = LeapHybridSampler()
    #sampler = ExactSolver()
    time4 = datetime.now()
    print(time4 - time3)

    time1 = datetime.now()
    sampleset = sampler.sample(bqm)
    time2 = datetime.now()
    solverTime = time2 - time1
    time7 = datetime.now()
    sample = sampleset.first.sample
    energy = sampleset.first.energy
    time8 = datetime.now()
    print(time8 - time7)

    time9 = datetime.now()
    # Build solution from returned binary variables:
    selected_item_indices = []
    for varname, value in sample.items():
        # For each "x" variable, check whether its value is set, which
        # indicates that the corresponding item is included in the
        # knapsack
            # The index into the weight array is retrieved from the
            # variable name
        if(sample[varname] == 1):
            selected_item_indices.append(int(varname))
    time10 = datetime.now()
    print(time10 - time9)

    #for i in solved.keys():
    #    selected_item_indices.append(i)

    return sorted(selected_item_indices), energy, solverTime, sampleset

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

if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else "sample.csv"
    incidencias, controles, df = createList(path)

    time1 = datetime.now()
    selected_item_indices, energy, solverTime, sampleset = solve_knapsack(incidencias, controles)
    time2 = datetime.now()
    totalTime = time2 - time1
    selected_time = list(df.loc[selected_item_indices,'Tiempo'])

    print("Found solution at energy {}".format(energy))
    print("Selected item numbers (0-indexed):", selected_item_indices)
    print("Total time: ", totalTime)
    print("Total time spent in the solver: ", solverTime)
    print("Selected item time: {}, total = {}".format(selected_time, sum(selected_time)))