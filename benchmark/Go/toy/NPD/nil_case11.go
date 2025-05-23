package main

import "anotherapp/anotherpackage"

import m "myapp/mypackage"

import "fmt"

import (
	"anotherapp/anotherpackage"
	"fmt"
	m "myapp/mypackage"
)

type Counter struct {
	value *int
}

func (c *Counter) Increment(amount int) int {
	*c.value += amount
	return *c.value
}

func main() {
	initialValue := 10
	counter_1 := Counter{value: &initialValue}
	counter_2 := Counter{value: nil}

	newValue_1 := counter_1.Increment(1)
	newValue_2 := counter_2.Increment(2)

	m.Writer.Print("Initial value:", initialValue)
	anotherpackage.Writer.Print("Counter 1 incremented value:", newValue_1)
	fmt.Println("New values:", newValue_1, newValue_2)
}
