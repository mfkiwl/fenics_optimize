import optfx as of
import numpy as np
import ufl

def strain_to_voigt(e):
    return of.as_vector((e[0, 0], e[1, 1], 2*e[0, 1]))

def stress_from_voigt(sigma_voigt):
    return of.as_matrix(((sigma_voigt[0], sigma_voigt[2]), (sigma_voigt[2], sigma_voigt[1])))

def rotation_matrix(Q, theta):
    c = of.cos(theta)
    s = of.sin(theta)
    T = of.as_matrix([[c**2, s**2, -2*c*s],
                   [s**2, c**2, 2*c*s],
                   [c*s, -c*s, c**2-s**2]])
    return T*Q*ufl.transpose(T)

class NLProblem(of.NonlinearProblem):
    def __init__(self, J, F, bcs):
        self.bilinear_form = J
        self.linear_form = F
        self.bcs = bcs
        of.NonlinearProblem.__init__(self)

    def F(self, b, x):
        of.assemble(self.linear_form, tensor=b)
        for bc in self.bcs:
            bc.apply(b, x)

    def J(self, A, x):
        of.assemble(self.bilinear_form, tensor=A)
        for bc in self.bcs:
            bc.apply(A)

def eig_strain(E, U):
    #major = 0.5*(E[0, 0]+E[1, 1]) + ufl.sqrt((0.5*(E[0, 0]-E[1, 1]))**2+E[0, 1]**2)
    #minor = 0.5*(E[0, 0]+E[1, 1]) - ufl.sqrt((0.5*(E[0, 0]-E[1, 1]))**2+E[0, 1]**2)
    value = 2*E[0, 1]/(E[0, 0]-E[1, 1])
    C = of.project(((E[0, 0]+E[1, 1])/2), U)
    theta = 0.5*ufl.atan_2(value, 1)
    theta_90 = of.project(0.5*ufl.atan_2(value, 1) + of.Constant(np.pi/2), U)
    theta_90_minus = of.project(0.5*ufl.atan_2(value, 1) + of.Constant(np.pi + np.pi/2), U)
    theta_c = of.conditional(of.ge(0, C), of.conditional(of.ge(E[0, 0], C), theta_90, theta), of.conditional(of.ge(E[0, 0], C), theta, theta_90_minus))

    return theta_c, C