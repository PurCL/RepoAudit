public class TestCase2 {
    public static int test2_process(String data) {
        return data.length();
    }
    public static int test2_caller() {
        String data = null;
        return test2_process(data);
    }
    
    public static void main(String[] args) {
        try {
            test2_caller();
        } catch (Exception e) {
            System.out.println("Case 2 Exception: " + e);
        }
    }
}