function f(n:integer):integer {if(n==0){return 0;}else{return g(n-1);}} function g(n:integer):integer {return f(n);} print(f(2));
