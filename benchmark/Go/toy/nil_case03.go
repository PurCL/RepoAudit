package main

import "fmt"

func main() {
    var slice []int // nil slice
    fmt.Println(slice[0]) // Panic: runtime error: index out of range [0] with length 0
}
