//webpack.config.js

const path = require('path')

const config = {
  entry: './jssrc/app.js',
  output: {
    path: path.resolve(__dirname, 'jsdist'),
    filename: 'bundle.js'
  },
  module: {
    rules: [
      { test: /\.js$/,
        loader: 'babel-loader',
        exclude: /node_modules/
      }
    ]
  }
}

module.exports = config