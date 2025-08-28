function hello() {
    let output = [];

    for (let i = 0; i < 5; i++) {
        output.push(null);
    }
    return output;
}

function hello2() {
    let output = hello();
    for (let i = 0; i < 4; i++) {
        output[i] = i.toString();
    }
    return output[4].length;
}

