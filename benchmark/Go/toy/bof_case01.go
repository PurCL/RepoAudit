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

func main() {
    // Create an instance of MyType and call its method.
    obj := MyType{Name: "Alice"}
    obj.Greet()

    // Call the standalone function.
    result := Add(10, 20)
    fmt.Printf("The result of Add is: %d\n", result)

    arr := [3]int{1, 2, 3}
    fmt.Println(arr[5]) // Panic: index out of range [5] with length 3
}
