import sympy
from sympy import Matrix


def find_unit_solution(A):
    # Convert the input matrix A to a SymPy Matrix
    A_sym = Matrix(A)

    # Compute the nullspace of A over the rational numbers
    null_space = A_sym.nullspace()

    if not null_space:
        return None  # No non-trivial solution exists

    # Since rank is N-1, the nullspace is one-dimensional
    # Take the first basis vector of the nullspace
    x = null_space[0]

    # Scale the vector to make all components integers
    denominators = [term.q for term in x]  # Get denominators of the fractions
    lcm_denominator = sympy.lcm(denominators)  # Least common multiple of denominators
    x_int = x * lcm_denominator  # Scale to make all entries integers

    # Convert components to integers
    x_int_list = [int(term) for term in x_int]

    # Ensure the components are coprime (GCD is 1)
    gcd = sympy.gcd(x_int_list)
    x_unit = [term // gcd for term in x_int_list]

    return x_unit


# Example usage
if __name__ == "__main__":
    # Example matrix A
    A = [[1, 1, 0],
         [0, 0, 1]]

    solution = find_unit_solution(A)
    print("Unit solution x:", solution)
