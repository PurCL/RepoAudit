package main

import "fmt"

func test6_main() {
    var p *int = nil 
    fmt.Println(*p)
}

func main() {
    test6_main()
}