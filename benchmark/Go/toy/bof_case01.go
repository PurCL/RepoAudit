package main

import "fmt"

func main() {
    arr := [3]int{1, 2, 3}
    fmt.Println(arr[5]) // Panic: index out of range [5] with length 3
}
