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
      { test: /\.jsx?$/,
        loader: 'babel-loader',
        exclude: /node_modules/
      },
      { test: /\.css$/, use: [ 'style-loader', 'css-loader' ] }
    ]
  }
}

module.exports = config