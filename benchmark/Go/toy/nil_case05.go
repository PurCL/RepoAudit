package main

import "fmt"

func main() {
    var m map[string]int // nil map
    m["key"] = 42 // Panic: runtime error: invalid memory address or nil pointer dereference
}
