public class MultiFunctionDemo {

    public static void main(String[] args) {
        greetUser("Developer");

        int number = 5;
        System.out.println("Factorial of " + number + " is " + factorial(number));

        int a = 28, b = 35;
        System.out.println("GCD of " + a + " and " + b + " is " + gcd(a, b));

        int testNumber = 19;
        if (isPrime(testNumber)) {
            System.out.println(testNumber + " is a prime number.");
        } else {
            System.out.println(testNumber + " is not a prime number.");
        }
    }

    // Prints a greeting message to the user
    private static void greetUser(String name) {
        System.out.println("Hello, " + name + "! Welcome to MultiFunctionDemo.");
        printSeparator();
    }

    // Computes the factorial of n using recursion
    private static long factorial(int n) {
        if (n <= 1) {
            return 1;
        }
        // Inter-procedural call: recursive call then printing interim result
        long result = n * factorial(n - 1);
        System.out.println("Computed factorial(" + n + ") = " + result);
        return result;
    }

    // Computes the greatest common divisor using Euclid's algorithm.
    // This function calls itself recursively.
    private static int gcd(int a, int b) {
        if (b == 0) {
            return a;
        }
        // Inter-procedural call: next iteration of gcd
        return gcd(b, a % b);
    }

    // Checks if a number is prime by testing divisibility using a helper function.
    private static boolean isPrime(int n) {
        if (n <= 1) {
            return false;
        }
        for (int i = 2; i <= Math.sqrt(n); i++) {
            // Inter-procedural call: using helper function to check divisibility
            if (dividesEvenly(n, i)) {
                return false;
            }
        }
        return true;
    }

    // Helper function: checks if 'divisor' divides 'number' evenly.
    private static boolean dividesEvenly(int number, int divisor) {
        return number % divisor == 0;
    }

    // Prints a separator line
    private static void printSeparator() {
        System.out.println("--------------------------------------------------");
    }
}