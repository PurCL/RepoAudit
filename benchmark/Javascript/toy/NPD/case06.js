function main() {
    const obj = {
        greet() {
            let obj = 1;
            console.log("hello");
        }
    };
    
    
    const a = obj;
    
    function exec() {
        var b = null;
        let c = 1;
        if (true) {
            a = b;
        }
        for (let i = 0; i < 5; i++) {
            a.greet();
        }
    }
    
    exec();
}
