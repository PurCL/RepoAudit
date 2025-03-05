package main

import "fmt"

func main() {
    var slice []int
    slice[0] = 1 // Panic: runtime error: index out of range [0] with length 0
}
