from setuptools import setup, find_packages

setup(
    name="risk-compliance",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "pandas>=1.5.0",
        "numpy>=1.22.0",
        "pyyaml>=6.0",
        "shared-services>=0.1.0",
        "google-cloud-firestore>=2.0.0",
        "google-cloud-storage>=2.0.0",
        "google-cloud-pubsub>=2.0.0",
    ],
    author="AI Trading Machine Team",
    author_email="team@aitradingmachine.com",
    description="Risk and compliance module for AI Trading Machine",
    python_requires=">=3.8",
)
