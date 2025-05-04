package testcases.CWE15_External_Control_of_System_or_Configuration_Setting;

import java.io.IOException;
import java.net.*;

public class Main {
  int x;

  public int good(int k) {
      System.out.println("test");
      float y;
      y = 0.0f;

      int z = 0;

      int u = ClassA.z;

      u = ClassA.z;

      u = u / y;

      if (k > 0) {
        return z;
      } else if (k < 0){
        return u;
      } else {
        return 0;
      }
  }

  public void hoo2(int a) throws Throwable
  {
     int data = a;

     IO.writeLine("foo2: 100/" + data + " = " + (100 / data) + "\n");
  }

  public void bad(HttpServletRequest request, HttpServletResponse response) throws Throwable
    {
        String data;

        data = ""; /* Initialize data */

        if (data != null)
        {
            /* POTENTIAL FLAW: Display of data in web page after using replaceAll() to remove script tags, which will still allow XSS with strings like <scr<script>ipt> (CWE 182: Collapse of Data into Unsafe Value) */
            response.getWriter().println("<br>bad(): data = " + data.replaceAll("(<script>)", ""));
        }

    }



  public static void main(String[] args) {
    Main myObj1 = new Main();  // Object 1
    Main myObj2 = new Main();  // Object 2
    int s = 0;
    int t = 0;
    t = good(s);

    System.out.println(myObj1.x);
    System.out.println(myObj2.x);
  }
}