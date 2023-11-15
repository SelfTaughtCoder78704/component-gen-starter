import os
from flask import Flask, request, send_file, render_template, after_this_request
from langchain.chains import LLMChain
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import shutil

load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    # Ensure the file extension is .txt
    if 'file' not in request.files:
        return 'No file part', 400

    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400

    if file and allowed_file(file.filename):
        fn = request.form['file_extension']
        file_contents = file.read().decode('utf-8')
        zip_path = generate_components(fn, file_contents)

        @after_this_request
        def remove_file(response):
            try:
                os.remove(zip_path)
            except Exception as error:
                app.logger.error("Error removing or closing downloaded file handle", error)
            return response

        return send_file(zip_path, as_attachment=True, download_name='components.zip')
    else:
        return 'Invalid file type, only .txt files are allowed', 400

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() == 'txt'
    

def generate_components(fn, file_contents):
    allowed_extensions = ['.js','.jsx','.tsx','.svelte','.vue','.erb']
    if fn not in allowed_extensions:
        return 'Invalid file extension, only .js, .jsx, .tsx, .svelte, .vue, and .erb files are allowed', 400
    os.environ["OPENAI_API_KEY"] = OPENAI_KEY
    llm = OpenAI(temperature=0.2)

    language, extra_instructions = determine_language_instructions(fn)

    prompt_template = f"Create a component in {language} for: {{component}}. {extra_instructions}"
    prompt = PromptTemplate(
        input_variables=["component"],
        template=prompt_template,
    )
    chain = LLMChain(llm=llm, prompt=prompt)

    components_dir = os.path.join(os.getcwd(), 'components')
    if not os.path.exists(components_dir):
        os.mkdir(components_dir)

    question_list = [line.strip() for line in file_contents.split('\n')]
    for thing in question_list:
        file_name, valid = process_line(thing, fn)
        if not valid:
            continue
        component_path = os.path.join(components_dir, file_name)
        with open(component_path, "w") as f:
            f.write(chain.run(thing))

    zip_path = os.path.join(os.getcwd(), 'components.zip')
    shutil.make_archive('components', 'zip', components_dir)
    shutil.rmtree(components_dir)
    return zip_path

def determine_language_instructions(fn):
    if fn == '.js':
        language = "vanilla JavaScript"
        extra_instructions = "Write a plain JavaScript function to create a DOM element for the component. Do not use HTML or any frameworks like React."
    else:
        language = fn
        extra_instructions = 'dont forget to export the component properly'
    return language, extra_instructions

def process_line(line, fn):
    parts = line.split(":")
    if len(parts) < 2:
        print("Invalid input:", line)
        return None, False
    file_name = parts[1].split(" -")[0].strip() + fn
    return file_name, True


if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("PORT", default=5000))
