const obj = {
    greet() {
        let obj = 1;
        console.log("hello");
    }
};


const a = obj;

function call(items) {
    a = items;
}

const exec = function () {
    var b = null;
    let c = 1;
    call(b);

    for (let i = 0; i < 5; i++) {
        a.greet();
    }
}

exec();