import pandas as pd
import dimod
import neal
from dimod import BinaryQuadraticModel
from dwave.system import LeapHybridSampler
import sys
from datetime import datetime

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

    return incidencias, controles, dataframe

def createBQM(incidencias, controles):

    idIncidencias = incidencias.keys()
    idControles = controles.keys()
    Q = dimod.AdjVectorBQM(dimod.Vartype.BINARY)

    tiempos = []
    for i in idIncidencias:
        tiempos.append(incidencias[i]['tiempo'])

    penalizacion = max(tiempos) + 1

    for i, j in zip(idIncidencias, range(len(idIncidencias))):
        Q.set_linear('x' + str(i), tiempos[j])

    for k in idControles:
        cIncidencias = controles[k]
        for i in cIncidencias:
            key = ('x' + str(i))

            Q.linear[key] -= penalizacion

    for i in range(len(idIncidencias)):
        for j in range(i + 1, len(idIncidencias)):
            incidencia1 = list(idIncidencias)[i]
            incidencia2 = list(idIncidencias)[j]
                
            key = ('x' + str(incidencia1), 'x' + str(incidencia2))
                
            Q.quadratic[key] = 0

    for k in idControles:
        cIncidencias = controles[k]
        for i in range(len(cIncidencias)):
            for j in range(i + 1, len(cIncidencias)):
                incidencia1 = cIncidencias[i]
                incidencia2 = cIncidencias[j]
                
                key = ('x' + str(incidencia1), 'x' + str(incidencia2))
                
                Q.quadratic[key] += 2 * penalizacion

    return Q

def solve_knapsack(incidencias, controles, sampler=None):
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
    bqm = createBQM(incidencias, controles)



    if sampler is None:
        sampler = LeapHybridSampler()

    sampleset = sampler.sample(bqm)
    sample = sampleset.first.sample
    energy = sampleset.first.energy

    # Build solution from returned binary variables:
    selected_item_indices = []
    for varname, value in sample.items():
        # For each "x" variable, check whether its value is set, which
        # indicates that the corresponding item is included in the
        # knapsack
        if value and varname.startswith('x'):
            # The index into the weight array is retrieved from the
            # variable name
            selected_item_indices.append(int(varname[1:]))

    return sorted(selected_item_indices), energy

if __name__ == '__main__':

    path = sys.argv[1] if len(sys.argv) > 1 else "sample.csv"
    incidencias, controles, df = createList(path)

    time1 = datetime.now()
    selected_item_indices, energy = solve_knapsack(incidencias, controles)
    time2 = datetime.now()
    totalTime = time2 - time1
    #selected_time = list(df.loc[selected_item_indices,'Tiempo'])

    print("Found solution at energy {}".format(energy))
    print("Selected item numbers (0-indexed):", selected_item_indices)
    print("Total time: ", totalTime)
    #print("Selected item time: {}, total = {}".format(selected_time, sum(selected_time)))