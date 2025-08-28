function hello5() {
    let output = [];

    for (let i = 0; i < 5; i++) {
        output.push(null);
    }
    return output;
}

function hello6() {
    let output = hello5();
    for (let i = 0; i < 4; i++) {
        output[i] = i.toString();
    }
    if (output[4] !== null && output[4] !== undefined) {
        return output[4].length;
    }
    return 0;
}

