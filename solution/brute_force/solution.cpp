#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

// 暴力解法 - O(n^2)
int main() {
    int n;
    cin >> n;
    vector<int> a(n);
    for (int i = 0; i < n; i++) {
        cin >> a[i];
    }

    // 读取查询
    int q;
    cin >> q;
    for (int i = 0; i < q; i++) {
        int x;
        cin >> x;
        
        // 暴力查找位置
        vector<int> sorted = a;
        sort(sorted.begin(), sorted.end(), greater<int>());
        
        int position = -1;
        for (int j = 0; j < n; j++) {
            if (sorted[j] == x) {
                position = j + 1; // 1-based indexing
                break;
            }
        }
        
        cout << position << endl;
    }
    
    return 0;
} 