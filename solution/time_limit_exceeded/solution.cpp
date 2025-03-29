#include <iostream>
#include <vector>
#include <algorithm>
#include <unistd.h>
using namespace std;

// 超时解法 - O(n^3)，添加额外延迟
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
        
        // 添加不必要的计算和延迟
        vector<int> sorted = a;
        
        // 低效的排序方式（冒泡排序）
        for (int j = 0; j < n; j++) {
            for (int k = 0; k < n - j - 1; k++) {
                if (sorted[k] < sorted[k + 1]) {
                    swap(sorted[k], sorted[k + 1]);
                }
                
                // 故意添加无用的运算
                for (int l = 0; l < min(100, n); l++) {
                    int dummy = sorted[l % n] * l;
                    if (dummy < 0) cout << ".";  // 不会执行，只是为了防止优化
                }
            }
        }
        
        int position = -1;
        for (int j = 0; j < n; j++) {
            if (sorted[j] == x) {
                position = j + 1; // 1-based indexing
                break;
            }
        }
        
        // 在大型测试用例上添加小延迟
        if (n > 100) {
            usleep(1000); // 延迟1毫秒
        }
        
        cout << position << endl;
    }
    
    return 0;
} 