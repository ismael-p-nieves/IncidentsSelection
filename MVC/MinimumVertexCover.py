from math import ceil
from math import log2
from os import times
import sys
from datetime import datetime
from typing import Dict
import dimod
from dimod.reference.samplers.exact_solver import ExactSolver
from dwave.system import LeapHybridSampler
import pandas as pd
import dwave.inspector
from dwave.system.composites.embedding import EmbeddingComposite
from dwave.system import DWaveSampler, EmbeddingComposite

def addControl(controles, idControl, idIncidencia):
    #Este método se dedica a relacionar las incidencias con los controles que la componen.

    for i in controles.keys():
        if i == idControl:  #Si el control ya está en el diccionario, se anexiona el id de la nueva incidencia.
            controles[i].append(int(idIncidencia))
            return controles

    controles[idControl] = [int(idIncidencia)]  #Si el control no está en el diccionario, se crea una nueva entrada junto a la 
                                                #incidencia.
    return controles

def createList(dataPath):
    incidencias = {}    #Las incidencias son las brechas de seguridad que surgen. El objetivo es seleccionar las incidencias
                        #justas y necesarias que gestionar.
                        #Cada entrada contiene la gravedad y el tiempo relacionado con la incidencia a la que corresponde la
                        #clave de acceso del diccionario.

    controles = {}      #Los controles son problemas específicos que componen las incidencias. Cuando se gestiona una incidencia,
                        #se resuelven todos los controles que la forman, y se solucionan para el resto de incidencias que tengan
                        #ese control. El objetivo es resolver todos los controles de forma que todas las ncidencias se resuelvan.
                        #El formato de este diccionario tiene como clave de acceso la id del control, y el contenido de la
                        #entrada contiene las ids de las incidencias del que forma parte.

    dataframe = dataframe = pd.read_csv(path, names=['IdIncidencia', 'IdAmenaza', 'Amenaza', 'Gravedad', 'IdControl', 'Control', 'Tiempo'])

    idInc = dataframe['IdIncidencia']   #El identificador de las incidencias.
    idCon = dataframe['IdControl']      #El identificador de los controles.
    grav = dataframe['Gravedad']        #La gravedad de la incidencia. Para este problema no lo usaremos.
    tiem = dataframe['Tiempo']          #El tiempo que se necesita para gestionar la incidencia.
    
    incidencias[int(idInc[0])] = {'gravedad': int(grav[0]), 'tiempo': int(tiem[0])}
    controles = addControl(controles, idCon[0], int(idInc[0]))   #Se inicializa la lista de incidencias con la primera fila.

    for i in range(1, len(dataframe.values)):
        if(idInc[i] != idInc[i-1]): #Comprueba que la incidencia es nueva o no comparando el id con el anterior.
                                    #NOTA: Esto solo funciona si la lista está ordenada por incidencias.
            incidencias[int(idInc[i])] = {'gravedad': int(grav[i]), 'tiempo': int(tiem[i])}

        controles = addControl(controles, idCon[i], int(idInc[i]))

    print(controles)
    
    return incidencias, controles, dataframe

def createBQM(incidencias, controles):
    idIncidencias = incidencias.keys()  #Se extraen las ids de las incidencias para mejor gestión.
    idControles = controles.keys()      #Se extraen las ids de los controles para mejor gestión.

    Q = dimod.AdjVectorBQM(dimod.Vartype.BINARY)    #Este es el formato principal del BQM, una matriz cuadrática.
    J = {}                                          #Este formato se utiliza para usarlo con el inspector.

    tiempos = []                        #Se extraen los tiempos para mejor gestión y para sacar el máximo.
    for i in idIncidencias:
        tiempos.append(incidencias[i]['tiempo'])

    y = {}
    slack_incidencias = {}

    for k in idControles:
        num_incidencias = len(controles[k])
        num_slack = ceil(log2(num_incidencias))
        slack_incidencias[k] = num_slack
        for i in range(num_slack): 
            if k in y:
                y[str(k)].append(2**i)
            else:
                y[str(k)] = [2**i]
                

    penalizacion = max(tiempos) + 10    #La penalización es el valor que nos va a ayudar a seleccionar qué incidencias tenemos
                                        #que seleccionar. La condición que necesitamos que se cumpla es que todos los controles
                                        #sean resueltos. Cualquier solución que no cumpla con esa condición, será descartada
                                        #gracias al valor de penalización. Se ha decidido que el valor sea el máximo tiempo 
                                        #entre todas las incidencias para que pueda variar según sea necesario, y es
                                        #incrementado en 1 para que no interfiera con el peso de las decisiones.
    
    #Término linear xi (-P*xi).
    #Este término linear se encarga de relacionar el tiempo que se tarda en gestionar una incidencia. De forma muy simplificada,
    #esto es lo que determinará qué incidencias son las mejores en caso de que haya varias soluciones válidas. Se recomienda leer
    #la documentación para una explicación en mayor detalle y cómo se ha llegado a esta operación.
    for i, j in zip(idIncidencias, range(len(idIncidencias))):
        Q.set_linear('x' + str(i), tiempos[j])
        J[(i, i)] = tiempos[j]

    #Término linear xi (-P*xi).
    #Esta parte se utiliza para restar la penalización a cada incidencia que resuelva un control. De forma muy simplificada, si
    #una incidencia resuelve varios controles, es más probable que sea seleccionada. Se recomienda leer la documentación para
    #una explicación en mayor detalle y cómo se ha llegado a esta operación.
    for k in idControles:
        cIncidencias = controles[k]     #Se extraen todas las incidencias de las que forma parte cada control, de forma que se
                                        #pueda usar para acceder al BQM.
        
        for i in cIncidencias:
            key = ('x' + str(i))

            Q.linear[key] -= penalizacion
            J[(i, i)] -= penalizacion

    #Término linear y-y (sk² + 2Psk)
    for k in idControles:
        if k in y:
            slacks = y[k]
            if type(slacks) is int:
                Q.set_linear('y' + str(k) + '-' + str(slacks), (slacks**2 + 2) * penalizacion)
            else:
                for i in slacks:
                    Q.set_linear('y' + str(k) + '-' + str(i), (i**2 + 2) * penalizacion)

    #Término cuadrático xi-xj (2P*xi*xj).
    #Esta parte sirve simplemente para inicializar los términos cuadráticos en el BQM.
    for k in idControles:
        cIncidencias = controles[k]
        for i in range(len(cIncidencias)):
            for j in range(i + 1, len(cIncidencias)):
                incidencia1 = cIncidencias[i]
                incidencia2 = cIncidencias[j]
            
                key = ('x' + str(incidencia1),'x' + str(incidencia2))
                
                Q.quadratic[key] = 0
                J[(incidencia1, incidencia2)] = 0

    #Término cuadrático xi-xj (2P*xi*xj).
    #El término cuadrático se encarga de evitar redundancias entre los controles. De forma muy simplificada, si un control es
    #resuelto por dos incidencias, puede ser que una de esas incidencias sea innecesaria. Se recomienda leer la documentación
    #para una explicación en mayor detalle y cómo se ha llegado a esta operación.
    for k in idControles:
        cIncidencias = controles[k]
        for i in range(len(cIncidencias)):
            for j in range(i + 1, len(cIncidencias)):
                incidencia1 = cIncidencias[i]
                incidencia2 = cIncidencias[j]
                
                key = ('x' + str(incidencia1),'x' + str(incidencia2))
                
                Q.quadratic[key] += 2 * penalizacion
                J[(incidencia1, incidencia2)] += 2 * penalizacion

    #Término cuadrático yi-yj
    for k in idControles:
        if k in y:
            slacks = y[k]
            if type(slacks) is not int:
                for i in range(len(slacks)):
                    for j in range(i + 1, len(slacks)):
                        slack1 = slacks[i]
                        slack2 = slacks[j]

                        key = ('y' + str(k) + '-' + str(i), 'y' + str(k) + '-' + str(j))
                        Q.quadratic[key] = 2 * penalizacion * slack1 * slack2

    #Término cuadrático y-x
    for k in idControles:
        if k in y:
            cIncidencias = controles[k]
            slacks = y[k]
            if type(slacks) is int:
                for i in range(len(cIncidencias)):
                    incidencia1 = cIncidencias[i]

                    key = ('x' + str(incidencia1), 'y' + str(k) + '-' + str(slacks))

                    Q.quadratic[key] = -2 * penalizacion * slacks
            else:
                for i in range(len(cIncidencias)):
                    for j in range(len(slacks)):
                        incidencia1 = cIncidencias[i]
                        slack1 = slacks[j]

                        key = ('x' + str(incidencia1), 'y' + str(k) + '-' + str(j))

                        Q.quadratic[key] = 2 * penalizacion * slack1

    print(Q)
        
    return Q, J

def solve_knapsack(incidencias, controles, online, sampler=None, samplerSpin=None):
    timeBqmS = datetime.now()
    bqm, J = createBQM(incidencias, controles)  #Se crea la matriz con las energías entre cada incidencia.
    timeBqmF = datetime.now()
    timeBQM = timeBqmF - timeBqmS
    print('Se han tardado ' + str(timeBQM) + ' segundos en crear el BQM.')

    timeSamplerS = datetime.now()
    if online:
        sampler = LeapHybridSampler()           #Se inicializa el sampler. El LeapHybridSampler se utiliza para conectarse a
    else:                                       #los ordenadores de D-Wave, y el ExactSolver para hacer una simulación en la
        sampler = ExactSolver()                 #computadora.
        #Probar SimulatedAnnealingSampler

    timeSamplerF = datetime.now()
    timeSampler = timeSamplerF - timeSamplerS
    print('Se han tardado ' + str(timeSampler) + ' segundos en crear el sampler.')

    timeSolverS = datetime.now()
    sampleset = sampler.sample(bqm)             #Se pasa el BQM que hemos creado anteriormente al sampler y busca las soluciones.
    timeSolverF = datetime.now()
    timeSolver = timeSolverF - timeSolverS
    print('Se han tardado ' + str(timeSolver) + ' segundos en resolver el problema.')

    sample = sampleset.first.sample             #Se guarda qué incidencias han sido gestionadas y cuáles no.
    energy = sampleset.first.energy             #Se guarda la energía que tiene la solución.

    #selected_item_ids = []
    #for varname, value in sample.items():
        # For each "x" variable, check whether its value is set, which
        # indicates that the corresponding item is included in the
        # knapsack
            # The index into the weight array is retrieved from the
            # variable name
        #if(sample[varname] == 1):
            #selected_item_ids.append(int(varname))

    selected_item_ids = []
    for varname, value in sample.items():
        # For each "x" variable, check whether its value is set, which
        # indicates that the corresponding item is included in the
        # knapsack
        if value and varname.startswith('x'):
            # The index into the weight array is retrieved from the
            # variable name
            selected_item_ids.append(int(varname[1:]))

    return sorted(selected_item_ids), energy, timeSolver, sampleset, J

if __name__ == '__main__':

    path = sys.argv[1] if len(sys.argv) > 1 else "/home/ismael/Escritorio/Cuantica/MVC/Eventos50.csv"

    if sys.argv[2].lower() != 'false' and str(sys.argv[2]).lower() != 'true':
        print('Se ha introducido el modo del sampler incorrectamenete.\nRecuerde que para el sampler offline se utiliza "false" y para el online se utiliza "true".')
        sys.exit()
    if sys.argv[2].lower() == 'true':
        online = True
    else:
        online = False

    incidencias, controles, dataframe = createList(path)

    timeTotalS = datetime.now()
    selected_item_ids, energy, timeSolver, sampleset, J = solve_knapsack(incidencias, controles, online)
    timeTotalF = datetime.now()
    timeTotal = timeTotalF - timeTotalS
    selected_time = list(dataframe.loc[selected_item_ids,'Tiempo'])

    #sampler = EmbeddingComposite(DWaveSampler(solver={'qpu': True}))
    #response = sampler.sample_qubo(J, num_reads=1000)
    #dwave.inspector.show(response)

    print("Encontrada solución con la energía {}".format(energy))
    print("Items seleccionados (0-indexed):", selected_item_ids)
    print("Tiempo total: ", timeTotal)
    print("Tiempo de los objetos seleccionados: {}, Total = {}".format(selected_time, sum(selected_time)))