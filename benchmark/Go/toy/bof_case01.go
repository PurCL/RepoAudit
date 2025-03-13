package main

import "fmt"

// MyType is a sample struct.
type MyType struct {
    Name string
}

// Greet is a method defined on MyType.
func (m MyType) Greet(a int) {
    fmt.Printf("Hello, %s!\n", m.Name)
}

// Add is a standalone function that returns the sum of two integers.
func Add(a int, b int) int {
    return a + b
}

// SumAndDiff returns two integers: their sum and their difference.
func SumAndDiff(a, b int) (int, int) {
    if a > b {
        return a + b, a - b
    }
    return a + b, b - a
}

// PrintMessage prints the provided message. It may exit early without returning any value.
func PrintMessage(msg string) {
    if msg == "" {
        // Early return without any value (since the function returns nothing).
        return
    }
    fmt.Println(msg)
}

func main() {
    // Create an instance of MyType and call its method.
    obj := MyType{Name: "Alice"}
    obj.Greet(2)

    // Call the standalone function.
    result := Add(10, 20)
    fmt.Printf("The result of Add is: %d\n", result)

    arr := [3]int{1, 2, 3}
    fmt.Println(arr[5]) // Panic: index out of range [5] with length 3
}
