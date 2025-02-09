import pandas as pd


def print_coloured(text, color_code):
    print(f"\033[{color_code}m{text}\033[0m")
    
def compare_test(file):
    file1 = 'data/test/games.csv'
    file2 = file

    df1 = pd.read_csv(file1)
    df2 = pd.read_csv(file2)

    def compare_csv(df1, df2):
        if not df1.columns.equals(df2.columns):
            print("The columns are different:")
            print(f"Columns in first file: {df1.columns}")
            print(f"Columns in second file: {df2.columns}")
            return

        comparison = df1.compare(df2)
        
        if not comparison.empty:
            print_coloured("Test data not equivalent", "31")
            ch = int(input("enter -1 to see diff: "))
            if ch == -1:
                print(comparison)
        else:
            print_coloured("Test data equivalent", "32")

    compare_csv(df1, df2)
