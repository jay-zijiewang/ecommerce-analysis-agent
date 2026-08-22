from src.agent import run_agent


def main() -> None:
    """Run the interactive command-line application."""

    print("E-commerce Analysis Agent")
    print("Type exit or quit to stop the program.")

    while True:
        question = input("\nQuestion: ").strip()

        if question.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        if not question:
            continue

        try:
            answer = run_agent(question)
        except Exception as error:
            print(f"\nError: {error}")
            continue

        print("\nAnalysis:\n")
        print(answer)


if __name__ == "__main__":
    main()