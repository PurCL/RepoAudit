package main

import "fmt"

type test1_MyStruct struct {
    Name string
}

func (m *test1_MyStruct) test1_PrintName() {
    fmt.Println(m.Name) 
}

func test1_main() {
    var s *test1_MyStruct 
    s.PrintName()    
}

func main() {
	test1_main()
}