import java.io.*;
import java.util.*;

public class solution {
    public static void main(String[] args) throws IOException {
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        PrintWriter pw = new PrintWriter(System.out);
        
        int n = Integer.parseInt(br.readLine().trim());
        Integer[] a = new Integer[n];
        String[] line = br.readLine().trim().split(" ");
        for (int i = 0; i < n; i++) {
            a[i] = Integer.parseInt(line[i]);
        }
        
        // Sort in descending order
        Arrays.sort(a, Collections.reverseOrder());
        
        // Process queries
        int q = Integer.parseInt(br.readLine().trim());
        for (int i = 0; i < q; i++) {
            int query = Integer.parseInt(br.readLine().trim());
            int position = Arrays.asList(a).indexOf(query);
            pw.println(position == -1 ? -1 : position + 1);
        }
        
        pw.close();
    }
} 