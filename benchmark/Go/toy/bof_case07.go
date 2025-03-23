package main

import (
	"fmt"
	"errors"
)

func createSlice(size int) ([]int, error) {
	if size <= 0 {
		return nil, errors.New("invalid size")
	}
	return make([]int, size), nil
}

func populateSlice(slice []int, value int) {
	for i := 0; i < len(slice); i++ {
		slice[i] = value
	}
}

func accessElement(slice []int, index int) {
	fmt.Println(slice[index])
}

func processElements(slice []int) {
	for i := 0; i < len(slice)+2; i++ {
		if i < len(slice) {
			fmt.Printf("Processing slice[%d]: %d\n", i, slice[i])
		} else {
			accessElement(slice, i)
		}
	}
}

func conditionalAccess(slice []int, condition bool) {
	if condition {
		if len(slice) > 2 {
			fmt.Println("Accessing safe index:", slice[2])
		} else {
			fmt.Println("Index is out of bounds in safe condition!")
		}
	} else {
		accessElement(slice, 10)
	}
}

func manipulateAndAccess(slice []int) {
	for i := 0; i < len(slice)+5; i++ {
		if i < len(slice) {
			slice[i] = i * 10
			fmt.Println("Updated slice:", slice)
		} else {
			accessElement(slice, i)
		}
	}
}

func populateMap() map[int]string {
	m := make(map[int]string)
	for i := 0; i < 10; i++ {
		m[i] = fmt.Sprintf("Element %d", i)
	}
	return m
}

func processMapElements(m map[int]string) {
	for i := 0; i < len(m)+2; i++ {
		if value, exists := m[i]; exists {
			fmt.Println("Processing map value:", value)
		} else {
			fmt.Println("Safe check: No map element at index", i)
		}
	}
}

func main() {
	slice, err := createSlice(5)
	if err != nil {
		fmt.Println("Error creating slice:", err)
		return
	}

	populateSlice(slice, 100)

	processElements(slice)

	conditionalAccess(slice, false)

	manipulateAndAccess(slice)

	m := populateMap()
	processMapElements(m)
}
