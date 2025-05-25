package main

import "fmt"

func main() {
    var p *int
    fmt.Println(*p) // Panic: runtime error: invalid memory address or nil pointer dereference
}
