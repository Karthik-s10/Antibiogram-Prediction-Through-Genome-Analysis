"""
Auto-run after pip install to download VC++ Redistributables.
This file is automatically executed by pip if placed correctly.
"""
try:
    import install_vc_redist
    install_vc_redist.main()
except Exception:
    pass  # Fail silently if import fails

