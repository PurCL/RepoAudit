package main

import "fmt"

func accessElement(slice []int) {
    fmt.Println(slice[5]) 
}

func main() {
    slice := []int{10, 20, 30}
    
    accessElement(slice) 
}
