package main

import "fmt"

type MyStruct struct {
    Name string
}

func (m *MyStruct) PrintName() {
    fmt.Println(m.Name) // Panic if m is nil
}

func main() {
    var s *MyStruct // nil pointer
    s.PrintName()    // Panic: runtime error: invalid memory address or nil pointer dereference
}
