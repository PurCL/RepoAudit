const obj = {
    greet() {
        console.log("hello");
    }
};

const a = obj;

function exec() {
    delete a.greet;
    a.greet();
}

exec();
