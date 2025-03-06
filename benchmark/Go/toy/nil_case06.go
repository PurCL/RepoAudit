package main

import "fmt"

func main() {
    var f func() // nil function pointer
    f()          // Panic: runtime error: invalid memory address or nil pointer dereference
}
