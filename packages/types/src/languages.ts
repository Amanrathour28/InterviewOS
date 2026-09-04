export interface LanguageConfig {
  id: string;
  name: string;
  extension: string;
  defaultFileName: string;
  monacoLanguage: string;
  starterCode: string;
}

export const SUPPORTED_CODING_LANGUAGES: LanguageConfig[] = [
  {
    id: 'python',
    name: 'Python',
    extension: '.py',
    defaultFileName: 'main.py',
    monacoLanguage: 'python',
    starterCode: `def solve():\n    # Write your solution here\n    print("Hello, InterviewOS!")\n\nif __name__ == "__main__":\n    solve()\n`,
  },
  {
    id: 'javascript',
    name: 'JavaScript (Node.js)',
    extension: '.js',
    defaultFileName: 'index.js',
    monacoLanguage: 'javascript',
    starterCode: `function solve() {\n    // Write your solution here\n    console.log("Hello, InterviewOS!");\n}\n\nsolve();\n`,
  },
  {
    id: 'typescript',
    name: 'TypeScript',
    extension: '.ts',
    defaultFileName: 'index.ts',
    monacoLanguage: 'typescript',
    starterCode: `function solve(): void {\n    // Write your solution here\n    console.log("Hello, InterviewOS!");\n}\n\nsolve();\n`,
  },
  {
    id: 'java',
    name: 'Java',
    extension: '.java',
    defaultFileName: 'Main.java',
    monacoLanguage: 'java',
    starterCode: `public class Main {\n    public static void main(String[] args) {\n        // Write your solution here\n        System.out.println("Hello, InterviewOS!");\n    }\n}\n`,
  },
  {
    id: 'cpp',
    name: 'C++',
    extension: '.cpp',
    defaultFileName: 'main.cpp',
    monacoLanguage: 'cpp',
    starterCode: `#include <iostream>\n\nint main() {\n    // Write your solution here\n    std::cout << "Hello, InterviewOS!" << std::endl;\n    return 0;\n}\n`,
  },
  {
    id: 'c',
    name: 'C',
    extension: '.c',
    defaultFileName: 'main.c',
    monacoLanguage: 'c',
    starterCode: `#include <stdio.h>\n\nint main() {\n    // Write your solution here\n    printf("Hello, InterviewOS!\\n");\n    return 0;\n}\n`,
  },
  {
    id: 'go',
    name: 'Go',
    extension: '.go',
    defaultFileName: 'main.go',
    monacoLanguage: 'go',
    starterCode: `package main\n\nimport "fmt"\n\nfunc main() {\n    // Write your solution here\n    fmt.Println("Hello, InterviewOS!")\n}\n`,
  },
  {
    id: 'rust',
    name: 'Rust',
    extension: '.rs',
    defaultFileName: 'main.rs',
    monacoLanguage: 'rust',
    starterCode: `fn main() {\n    // Write your solution here\n    println!("Hello, InterviewOS!");\n}\n`,
  },
  {
    id: 'sql',
    name: 'SQL (SQLite)',
    extension: '.sql',
    defaultFileName: 'query.sql',
    monacoLanguage: 'sql',
    starterCode: `-- Write your SQL query here\nSELECT 'Hello, InterviewOS!' AS message;\n`,
  },
];

export const getLanguageConfig = (id: string): LanguageConfig => {
  return (
    SUPPORTED_CODING_LANGUAGES.find((l) => l.id.toLowerCase() === id.toLowerCase()) ||
    SUPPORTED_CODING_LANGUAGES[0]
  );
};
