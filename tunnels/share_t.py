"""share mode: Gradio's built-in *.gradio.live tunnel. Zero setup (default)."""

GRADIO_PORT = 7860


def launch_share(demo, password: str, local_only: bool = False) -> None:
    if not local_only:
        print("[tunnel] share mode: public *.gradio.live URL will be printed below")
    demo.launch(
        share=not local_only,
        auth=("user", password),
        server_name="127.0.0.1" if local_only else "0.0.0.0",
        server_port=GRADIO_PORT,
    )
