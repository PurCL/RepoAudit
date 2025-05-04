package main

import "fmt"

func main() {
    m := make(map[int]int)

    go func() {
        m[1] = 10
    }()
    go func() {
        m[2] = 20
    }()

    fmt.Println(m)
}
