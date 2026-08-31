"""share mode: Gradio's built-in *.gradio.live tunnel. Zero setup (default)."""

GRADIO_PORT = 7860


def launch_share(demo, password: str) -> None:
    print("[tunnel] share mode: public *.gradio.live URL will be printed below")
    demo.launch(
        share=True,
        auth=("user", password),
        server_name="0.0.0.0",
        server_port=GRADIO_PORT,
    )
