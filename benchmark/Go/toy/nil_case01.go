package main

import "fmt"

func main() {
    p := new(int) // p is now a pointer to a newly allocated int
    *p = 42       // Assign a value to the memory location
    fmt.Println(*p) // Prints: 42
}