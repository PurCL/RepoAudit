package main

import "fmt"

type User struct {
	Name string
}

// Global variable — declared but not initialized (nil)
var globalUser *User

func printUserName() {
	// This will panic because globalUser is nil
	fmt.Println("User name:", globalUser.Name)
}

func main() {
	printUserName()
}
