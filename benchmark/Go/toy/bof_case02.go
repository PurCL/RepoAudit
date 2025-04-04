package main

import "fmt"

func main() {
    slice := []int{1, 2, 3}
    fmt.Println(slice[10]) // Panic: runtime error: index out of range [10] with length 3
}
