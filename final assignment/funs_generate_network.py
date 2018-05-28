from __future__ import division, unicode_literals, print_function

import numpy as np
import networkx as nx
import pandas as pd
from funs_dikes import Lookuplin  # @UnresolvedImport


def to_dict_dropna(data):
    return dict((str(k), v.dropna().to_dict())
                for k, v in pd.compat.iteritems(data))


def get_network():
    ''' Build network uploading crucial parameters '''

    # Upload dike info
    df = pd.read_excel('./data/dikeIjssel.xlsx', dtype=object)
    df = df.set_index('NodeName')

    nodes = df.to_dict('index')

    # Create network out of dike info
    G = nx.MultiDiGraph()
    for key, attr in nodes.items():
        G.add_node(key, **attr)

    # Select dike type nodes
    branches = df['branch'].dropna().unique()
    dike_list = df['type'][df['type'] == 'dike'].index.values
    dike_branches = {k: df[df['branch'] == k].index.values
                     for k in branches}

    # Upload fragility curves:
    frag_curves = pd.read_excel('./data/fragcurves/frag_curves.xlsx',
                                header=None, index_col=0).transpose()
    calibration_factors = pd.read_excel(
        './data/fragcurves/calfactors_pf1250.xlsx')

    # Upload room for the river projects:
    G.add_node('RfR_projects', **to_dict_dropna(
        pd.read_excel('./data/rfr_strategies.xlsx', index_col=0,
                      names=range(5))))
    G.node['RfR_projects']['type'] = 'measure'

    # Upload evacuation policies:
    G.add_node('EWS', **pd.read_excel('./data/EWS.xlsx').to_dict())
    G.node['EWS']['type'] = 'measure'

    # Upload muskingum params:
    Muskingum_params = pd.read_excel('./data/Muskingum/params.xlsx')

    # Fill network with crucial info:
    for dike in dike_list:
        # Assign fragility curves, assuming it's the same shape for every
        # location
        dikeid = 50001010
        G.node[dike]['f'] = np.column_stack((frag_curves.loc[:, 'wl'].values,
                                             frag_curves.loc[:, dikeid].values))
        # Adjust fragility curves
        G.node[dike]['f'][:, 0] += calibration_factors.loc[dike].values

        # Determine the level of the dike
        G.node[dike]['dikelevel'] = Lookuplin(G.node[dike]['f'], 1, 0, 0.5)

        # Assign stage-discharge relationships
        filename = './data/rating_curves/{}_ratingcurve_new.txt'.format(dike)
        G.node[dike]['r'] = np.loadtxt(filename)

        # Assign losses per location:
        name = './data/losses_tables/{}_lossestable.xlsx'.format(dike)
        G.node[dike]['table'] = pd.read_excel(name).values

        # Assign Muskingum paramters:
        G.node[dike]['C1'] = Muskingum_params.loc[G.node[dike]['prec_node'], 'C1']
        G.node[dike]['C2'] = Muskingum_params.loc[G.node[dike]['prec_node'], 'C2']
        G.node[dike]['C3'] = Muskingum_params.loc[G.node[dike]['prec_node'], 'C3']

    # The plausible 133 upstream wave-shapes:
    G.node['A.0']['Qevents_shape'] = pd.read_excel(
        './data/hydrology/wave_shapes.xls')

    G.add_node('discount rate', **{'value': 0})

    return G, dike_list, dike_branches
