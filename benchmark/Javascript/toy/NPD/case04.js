function hello3() {
    let output = [];

    for (let i = 0; i < 5; i++) {
        output.push(null);
    }
    return output;
}

function hello4() {
    let output = hello3();
    for (let i = 0; i < 4; i++) {
        output[i] = i.toString();
    }
    return output[4] ? output[4].length : 0;
}

