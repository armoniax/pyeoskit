import os
import sys
import shlex
import shutil
import subprocess
import tempfile
from . import log

logger = log.get_logger(__name__)

def find_eosio_cdt_path():
    eosio_cpp = shutil.which('eosio-cpp')
    if not eosio_cpp:
        raise Exception("eosio.cdt not installed, please refer to https://github.com/eosio/eosio.cdt for an installation guide")
    eosio_cpp = os.path.realpath(eosio_cpp)
    eosio_cpp = os.path.dirname(eosio_cpp)
    return os.path.dirname(eosio_cpp)

class cpp_compiler(object):

    def __init__(self, cpp_file, includes = [], entry='apply'):
        self.cpp_file = cpp_file
        self.includes = includes
        self.entry = entry
        if not cpp_file.endswith('.cpp'):
            raise Exception('Not a cpp file')

    def compile_cpp_file(self, opt='O3'):
        tmp_path = self.cpp_file[:-4]
        #%system rm test.obj test.wasm
        #%system eosio-cpp -I/usr/local/Cellar/eosio.cdt/1.6.1/opt/eosio.cdt/include/eosiolib/capi -I/usr/local/Cellar/eosio.cdt/1.6.1/opt/eosio.cdt/include/eosiolib/core -O3 -contract test -o test.obj -c test.cpp
        #%system eosio-ld test.obj -o test.wasm
        #%ls
        if sys.platform == 'darwin':
            dl_sufix = 'dylib'
        else:
            dl_sufix = 'so'
        eosio_cdt_path = find_eosio_cdt_path()
        clang_7_args = [f'{eosio_cdt_path}/bin/clang-7',
        '-o',
        f'{tmp_path}.obj',
        f'{tmp_path}.cpp',
        '--target=wasm32',
        '-ffreestanding',
        '-nostdlib',
        '-fno-builtin',
        '-fno-threadsafe-statics',
        '-fno-exceptions',
        '-fno-rtti',
        '-fmodules-ts',
        '-DBOOST_DISABLE_ASSERTS',
        '-DBOOST_EXCEPTION_DISABLE',
        '-Xclang',
        '-load',
        '-Xclang',
        f'{eosio_cdt_path}/bin/LLVMEosioApply.{dl_sufix}',
        f'-fplugin={eosio_cdt_path}/bin/eosio_plugin.{dl_sufix}',
        '-mllvm',
        '-use-cfl-aa-in-codegen=both',
        f'-I{eosio_cdt_path}/bin/../include/libcxx',
        f'-I{eosio_cdt_path}/bin/../include/libc',
        f'-I{eosio_cdt_path}/bin/../include',
        f'--sysroot={eosio_cdt_path}/bin/../',
        f'-I{eosio_cdt_path}/bin/../include/eosiolib/core',
        f'-I{eosio_cdt_path}/bin/../include/eosiolib/contracts',
        '-c',
        f'-I{eosio_cdt_path}/include/eosiolib/capi',
        f'-I{eosio_cdt_path}/include/eosiolib/core',
        f'-{opt}',
        '--std=c++17',
        ]
        for include in self.includes:
            clang_7_args.append(f"-I{include}")

        wasm_ld_args = [f'{eosio_cdt_path}/bin/wasm-ld',
        '--gc-sections',
        '--strip-all',
        '-zstack-size=8192',
        '--merge-data-segments',
        '-e', f'{self.entry}',
        '--only-export', f'{self.entry}:function',
        '-lc++',
        '-lc',
        '-leosio',
        '-leosio_dsm',
        '-mllvm',
        '-use-cfl-aa-in-codegen=both',
        f'{tmp_path}.obj',
        f'-L{eosio_cdt_path}/bin/../lib',
        '-stack-first',
        '--lto-O3',
        '-o',
        f'{tmp_path}.wasm',
        f'--allow-undefined-file={eosio_cdt_path}/bin/../eosio.imports']

        eosio_pp = [
            f'{eosio_cdt_path}/bin/eosio-pp',
            '-o',
            f'{tmp_path}.wasm',
            f'{tmp_path}.wasm',
        ]

        try:
            ret = subprocess.check_output(clang_7_args, stderr=subprocess.STDOUT)
            # logger.info(ret.decode('utf8'))
            ret = subprocess.check_output(wasm_ld_args, stderr=subprocess.STDOUT)
            # logger.info(ret.decode('utf8'))
            ret = subprocess.check_output(eosio_pp, stderr=subprocess.STDOUT)
            # logger.info(ret.decode('utf8'))
        except subprocess.CalledProcessError as e:
            logger.error("error (code {}):".format(e.returncode))
            logger.error(e.output.decode('utf8'))
            return None

        with open(f'{tmp_path}.wasm', 'rb') as f:
            return f.read()

def compile_cpp_file(src_path, includes=[], entry='apply', opt='O3'):
    compiler = cpp_compiler(src_path, includes, entry)
    return compiler.compile_cpp_file(opt)

def compile_cpp_src(account_name, code, includes = [], entry='apply', opt='O3', force=False):
    temp_dir = tempfile.mkdtemp()
    src_file = os.path.join(temp_dir, f'{account_name}.cpp')

    with open(src_file, 'w') as f:
        f.write(code)
    wasm_code = compile_cpp_file(src_file, includes, entry, opt=opt)

    shutil.rmtree(temp_dir)
    return wasm_code

def compile_with_eosio_cpp(contract_name, code, options=''):
    '''
    contract_name must match the class name in code, otherwise there will no abi generated
    '''
    temp_dir = tempfile.mkdtemp()
    logger.info(temp_dir)
    src_file = os.path.join(temp_dir, f'{contract_name}.cpp')
    wasm_file = os.path.join(temp_dir, f'{contract_name}.wasm')
    abi_file = os.path.join(temp_dir, f'{contract_name}.abi')

    with open(src_file, 'w') as f:
        f.write(code)
    eosio_cpp_args = f"eosio-cpp -o {wasm_file} {src_file}";
    eosio_cpp_args = shlex.split(eosio_cpp_args)

    try:
        ret = subprocess.check_output(eosio_cpp_args, stderr=subprocess.STDOUT)
        with open(wasm_file, 'rb') as f:
            code = f.read()
        abi = ''
        try:
            with open(abi_file, 'r') as f:
                abi = f.read()
        except Exception as e:
            logger.error(e)
        return code, abi
    except subprocess.CalledProcessError as e:
        logger.error("error (code {}):".format(e.returncode))
        logger.error(e.output.decode('utf8'))
        return None
    finally:
        shutil.rmtree(temp_dir)


class go_compiler(object):

    def __init__(self, go_file, includes = [], entry='apply'):
        self.go_file = go_file
        self.includes = includes
        self.entry = entry
        if not go_file.endswith('.go'):
            raise Exception('Not a go file')

    def compile_go_file(self, opt='O3'):
        tinygo = shutil.which('tinygo')
        if not tinygo:
            raise Exception('tinygo not found')
        wasm_file = self.go_file[:-3] + '.wasm'
        compile_cmd = [
            'tinygo',
            'build',
            '-x',
            '-gc=leaking',
            '-o',
            wasm_file+'.normal',
            '-target=eosio',
            '-wasm-abi=generic',
            '-scheduler=none',
            '-opt=z',
            '.'
        ]
        wasm2wast_cmd = [
            'eosio-wasm2wast',
            '-o',
            wasm_file[:-3]+'.wast',
            wasm_file+'.normal'
        ]
        wast2wasm_cmd = [
            'eosio-wast2wasm',
            '-o',
            wasm_file,
            wasm_file[:-3]+'.wast'
        ]

        mod_init_cmd = [
            'go',
            'mod',
            'init',
            'test'
        ]

        tidy_cmd = [
            'go',
            'mod',
            'tidy'
        ]

        src_path = os.path.dirname(self.go_file)
        os.chdir(src_path)
        try:
            ret = subprocess.check_output(mod_init_cmd, stderr=subprocess.STDOUT)
            ret = subprocess.check_output(tidy_cmd, stderr=subprocess.STDOUT)
            ret = subprocess.check_output(compile_cmd, stderr=subprocess.STDOUT)
            # logger.info(ret.decode('utf8'))
            ret = subprocess.check_output(wasm2wast_cmd, stderr=subprocess.STDOUT)
            # logger.info(ret.decode('utf8'))
            ret = subprocess.check_output(wast2wasm_cmd, stderr=subprocess.STDOUT)
            # logger.info(ret.decode('utf8'))
        except subprocess.CalledProcessError as e:
            logger.error("error (code {}):".format(e.returncode))
            logger.error(e.output.decode('utf8'))
            return None

        with open(wasm_file, 'rb') as f:
            return f.read()

def compile_go_file(src_path, includes=[], entry='apply', opt='O3'):
    compiler = go_compiler(src_path, includes, entry)
    return compiler.compile_go_file(opt)

def compile_go_src(account_name, code, includes = [], entry='apply', opt='O3', force=False):
    temp_dir = tempfile.mkdtemp()
    src_file = os.path.join(temp_dir, f'{account_name}.go')
    abi_file = os.path.join(temp_dir, f'{account_name}.abi')

    with open(src_file, 'w') as f:
        f.write(code)

    wasm_code = compile_go_file(src_file, includes, entry, opt=opt)

    abi = None
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            if file.endswith('.abi'):
                with open(os.path.join(root, file), 'r') as f:
                    abi = f.read()
                    break
        if abi:
            break

    shutil.rmtree(temp_dir)
    return wasm_code, abi
