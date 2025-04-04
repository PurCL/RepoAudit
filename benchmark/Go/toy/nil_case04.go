package main

import "fmt"

type MyStruct struct {
    Value int
}

func main() {
    var s *MyStruct // nil pointer to struct
    fmt.Println(s.Value) // Panic: runtime error: invalid memory address or nil pointer dereference
}
