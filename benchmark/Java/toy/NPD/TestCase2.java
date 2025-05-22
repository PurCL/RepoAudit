public class TestCase2 {
    public static int test2_process(String data) {
        return data.length();
    }
    public static int test2_caller() {
        String data = null;
        return test2_process(data);
    }
    
    public static void main(String[] args) {
        test2_caller();
    }
}