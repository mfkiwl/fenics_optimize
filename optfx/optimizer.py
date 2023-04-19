#! /usr/bin/python3
# -*- coding: utf-8 -*-
from dolfin import *
from dolfin_adjoint import *
import numpy as np
#from .utils import to_numpy, from_numpy 
from .utils import from_numpy, to_numpy
try:
    import nlopt as nl
except ImportError:
    raise ImportError('Optimizer depends on Nlopt.')

def optimize(problem, initials, wrt, setting, params, algorithm='LD_MMA'):
    problem_size = 0

    for initial in initials:
        problem_size += initial.vector().size()

    optimizer = nl.opt(getattr(nl, algorithm), problem_size)

    split_index = []
    index = 0
    for initial in initials:
        index += initial.vector().size()
        split_index.append(index)

    def eval(x, grad):
        xs = np.split(x, split_index)
        xs_fenics = [from_numpy(i, j) for i, j in zip(xs, initials)]
        cost = problem.forward(xs_fenics)
        grad[:] = np.concatenate(problem.backward())
        return cost

    constraints = []
    for attribute in dir(problem):
        if attribute.startswith('constraint'):
            constraints.append(attribute)

    if constraints:
        for constraint in constraints:
            def const(x, grad):
                measure = getattr(problem, constraint)()
                grad[:] = np.concatenate(problem.backward_constraint(constraint, wrt[constraint]))
                return measure
            globals()[constraint] = lambda x, grad: const(x, grad)
            optimizer.add_inequality_constraint(globals()[constraint], 1e-8)

    optimizer.set_min_objective(eval)
    for set in setting:
        getattr(optimizer, set)(setting[set])
    for param in params:
        optimizer.set_param(param, params[param])
    initial_numpy = np.concatenate([to_numpy(i) for i in initials])
    solution_numpy = optimizer.optimize(initial_numpy)
    solution_fenics = [from_numpy(i, j) for i, j in zip(np.split(solution_numpy, split_index), initials)]
    return tuple(solution_fenics)
