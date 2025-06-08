package bad;
public class Test02 {
    public static int test2_process(String data) {
        return data.length();
    }
    public static int test2_caller() {
        String data = null;
        return test2_process(data);
    }
    public static void test2_main(String[] args) {
        test2_caller();
    }

    public static void main(String[] args) {
        test2_main(args);
    }
}