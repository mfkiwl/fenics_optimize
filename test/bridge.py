from dolfin import *
from dolfin_adjoint import *
from morphogenesis import forward
from morphogenesis.Solvers import AMG2Dsolver
from morphogenesis.Filters import helmholtzFilter, hevisideFilter
from morphogenesis.FileIO import export_result
from morphogenesis.Elasticity import reducedSigma, epsilon
from morphogenesis.Optimizer import MMAoptimize, HSLoptimize
import numpy as np

E = 1.0e9
nu = 0.3
p = 3
target = 0.4
r = 0.1

mesh = RectangleMesh(Point(0, 0), Point(20, 10), 200, 100)
N = mesh.num_vertices()

x0 = np.zeros(N)

X = FunctionSpace(mesh, "CG", 1)
V = VectorFunctionSpace(mesh, "CG", 1)

class Bottom(SubDomain):
    def inside(self, x, on_boundary):
        return on_boundary and x[1] < 1e-10

def clamped_boundary(x, on_boundary):
    return on_boundary and x[0] < 1e-10 or x[0] > 19.999

@forward([X])
def evaluator(x):
    rho = hevisideFilter(helmholtzFilter(x[0], X, r))
    export_result(project(rho, FunctionSpace(mesh, 'CG', 1)), 'result/test.xdmf')
    facets = MeshFunction('size_t', mesh, 1)
    facets.set_all(0)
    bottom = Bottom()
    bottom.mark(facets, 1)
    ds = Measure('ds', subdomain_data=facets)
    f = Constant((0, -1e3))
    u = TrialFunction(V)
    v = TestFunction(V)
    a = inner(reducedSigma(rho, u, E, nu, p), epsilon(v))*dx
    L = inner(f, v)*ds(1)
    bc = DirichletBC(V, Constant((0, 0)), clamped_boundary)
    u_ = Function(V)
    A, b = assemble_system(a, L, [bc])
    solver = AMG2Dsolver(A, b)
    uh = solver.forwardSolve(u_, V, False)
    J = assemble(inner(reducedSigma(rho, uh, E, nu, p), epsilon(uh))*dx)
    #print('\rCost : {:.3f}'.format(J), end='|')
    return J

@forward([X])
def volumeResponce(x):
    rho_bulk = project(Constant(1.0), FunctionSpace(mesh, 'CG', 1))
    rho_0 = assemble(rho_bulk*dx)
    rho_f = assemble(hevisideFilter(helmholtzFilter(x[0], X, r))*dx)
    rel = rho_f/rho_0
    val = rel - target
    #print('Constraint : {:.3f}'.format(val), end='')
    return val

HSLoptimize(N, x0, evaluator, volumeResponce)