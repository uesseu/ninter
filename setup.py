from setuptools import setup, find_packages

setup(
    name='ninter',
    version='0.0.0',
    install_requires=['pandas', 'numpy'],
    # package_dir={'ninwavelets': 'ninwavelets'},
    packages=find_packages(),
    description='User friendly pipe between python and other interpreters.',
    long_description='''User friendly pipe between python, R and Deno.
    The code can be written like python code.''',
    url='https://github.com/uesseu/ninter',
    author='Shoichiro Nakanishi',
    author_email='sheepwing@kyudai.jp',
    license='MIT',
    zip_safe=False,
)
